"""
Projects RAG Service - Vector Store and Retrieval Augmented Generation

Main Function:
- search_projects(query, k) -> Returns top-k RAG-matched chunks

Features:
- Incremental updates (only adds new projects, doesn't rebuild from scratch)
- Monitors projects.jsonl for changes
- Uses FAISS vector store with HuggingFace embeddings
"""

import os
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, List, Dict, Optional

# Vector store and embeddings
LANGCHAIN_AVAILABLE = False

try:

    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS
    from langchain_core.documents import Document
    LANGCHAIN_AVAILABLE = True
except ImportError:
    print("⚠️ LangChain packages not available. Install with: pip install langchain-community faiss-cpu sentence-transformers")
    Document = Any

logger = logging.getLogger(__name__)

# Paths
PROJECTS_JSONL_PATH = Path(__file__).parent.parent / "carbon-intelligence" / "server" / "output" / "projects.jsonl"
VECTOR_STORE_PATH = Path(__file__).parent.parent / "carbon-intelligence" / "server" / "output" / "projects_vector_store"
INDEXED_IDS_FILE = VECTOR_STORE_PATH / "indexed_ids.json"


class ProjectsRAGService:
    """
    RAG service for carbon credit projects.
    Main function: search_projects(query, k) -> returns top-k chunks
    """
    
    def __init__(self, projects_path: str = None, vector_store_path: str = None):
        """Initialize the RAG service."""
        print("\n" + "=" * 70)
        print("🚀 INITIALIZING PROJECTS RAG SERVICE")
        print("=" * 70)
        
        self.projects_path = Path(projects_path) if projects_path else PROJECTS_JSONL_PATH
        self.vector_store_path = Path(vector_store_path) if vector_store_path else VECTOR_STORE_PATH
        self.indexed_ids_file = self.vector_store_path / "indexed_ids.json"
        
        self.vector_store: Optional[FAISS] = None
        self.embeddings = None
        self.text_splitter = None
        self._lock = threading.Lock()
        self._watch_thread = None
        self._stop_watching = False
        self.indexed_ids = set()
        
        self.bm25 = None
        self.bm25_docs = []
        
        if not LANGCHAIN_AVAILABLE:
            logger.error("❌ LangChain packages not available")
            return
        
        import os
        if os.environ.get("LLM_MODE") == "ollama":
            print("📥 Loading Ollama embedding model (nomic-embed-text)...")
            logger.info("🚀 Loading Ollama embedding model...")
            from langchain_community.embeddings import OllamaEmbeddings
            self.embeddings = OllamaEmbeddings(
                model="nomic-embed-text",
                base_url=os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
            )
            print("   ✓ Ollama embedding model loaded")
        else:
            print("📥 Loading HuggingFace embedding model...")
            logger.info("🚀 Loading embedding model...")
            
            import torch
            # Prevent meta tensor initialization issues
            torch.set_default_dtype(torch.float32)
            
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={
                    'device': 'cpu',
                    'trust_remote_code': False
                },
                encode_kwargs={
                    'normalize_embeddings': True,
                    'batch_size': 32
                },
                cache_folder=None,  # Use default HuggingFace cache
                multi_process=False
            )
            print("   ✓ Embedding model loaded: sentence-transformers/all-MiniLM-L6-v2")
        logger.info("✅ Embedding model loaded")
        
        # Text splitter for chunking
        print("✂️  Configuring text splitter (chunk_size=1000, overlap=200)")
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        
        # Load indexed IDs and initialize vector store
        print("📋 Loading indexed project IDs...")
        self._load_indexed_ids()
        
        self._ready = False  # Flag to indicate if vector store is ready
        
        print("🔍 Checking for existing vector store...")
        faiss_index_path = self.vector_store_path / "index.faiss"
        
        if faiss_index_path.exists():
            # Existing store found - load synchronously (fast)
            self._initialize_vector_store()
            self._rebuild_bm25()
        else:
            # No existing store - build in background thread so server can start
            print("   No existing vector store found - will build in background")
            print("   ⚡ Server will start immediately. RAG search available after build completes.")
            build_thread = threading.Thread(target=self._initialize_vector_store, daemon=True)
            build_thread.start()
        
        print("=" * 70 + "\n")
    
    # ============================================================================
    # HELPER FUNCTIONS
    # ============================================================================
    
    def _rebuild_bm25(self):
        """Rebuilds the BM25 index from the FAISS docstore."""
        if not self.vector_store: return
        import time
        start = time.time()
        try:
            from rank_bm25 import BM25Okapi
            docs = list(self.vector_store.docstore._dict.values())
            self.bm25_docs = docs
            tokenized_corpus = [doc.page_content.lower().split() for doc in docs]
            if tokenized_corpus:
                self.bm25 = BM25Okapi(tokenized_corpus)
                logger.info(f"⚡ Rebuilt BM25 index for {len(docs)} documents in {time.time()-start:.3f}s")
            else:
                self.bm25 = None
        except ImportError:
            logger.warning("rank_bm25 not installed, hybrid search unavailable")
            self.bm25 = None
    
    def _load_indexed_ids(self):
        """Load the set of already indexed project IDs."""
        if self.indexed_ids_file.exists():
            try:
                with open(self.indexed_ids_file, 'r') as f:
                    data = json.load(f)
                    self.indexed_ids = set(data.get('indexed_ids', []))
                logger.info(f"📋 Loaded {len(self.indexed_ids)} indexed project IDs")
            except Exception as e:
                logger.warning(f"⚠️ Could not load indexed IDs: {e}")
                self.indexed_ids = set()
    
    def _save_indexed_ids(self):
        """Save the set of indexed project IDs."""
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        with open(self.indexed_ids_file, 'w') as f:
            json.dump({'indexed_ids': list(self.indexed_ids)}, f)
    
    def _get_project_id(self, project: Dict) -> str:
        """Generate unique ID for a project."""
        project_id = project.get('id', '')
        name = project.get('name', '')
        registry = project.get('registry', '')
        unique_str = f"{project_id}|{name}|{registry}"
        import hashlib
        return hashlib.md5(unique_str.encode()).hexdigest()
    
    def _load_all_projects(self, limit: int = None) -> List[Dict]:
        """Load projects from JSONL file with optional limit."""
        projects = []
        if not self.projects_path.exists():
            logger.warning(f"⚠️ Projects file not found: {self.projects_path}")
            return projects
        
        with open(self.projects_path, 'r', encoding='utf-8') as f:
            for line in f:
                if limit is not None and len(projects) >= limit:
                    break
                try:
                    projects.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
        
        return projects
    
    def _get_new_projects(self) -> List[Dict]:
        """Get only new projects that haven't been indexed yet."""
        all_projects = self._load_all_projects(limit=1000)
        new_projects = []
        
        for project in all_projects:
            project_id = self._get_project_id(project)
            if project_id not in self.indexed_ids:
                new_projects.append(project)
        
        if new_projects:
            logger.info(f"🆕 Found {len(new_projects)} new projects to index")
        return new_projects
    
    def _create_documents(self, projects: List[Dict]) -> List[Document]:
        """Convert projects to LangChain Documents with chunking."""
        documents = []
        
        for project in projects:
            project_id = self._get_project_id(project)
            
            # Extract text content - use correct field names from JSONL
            name = project.get('project_name') or project.get('name', '').strip()
            description = project.get('description', '').strip()
            actual_project_id = project.get('project_id', '')  # The real ID from data
            
            # Clean HTML tags if any
            import re
            description = re.sub(r'<[^>]+>', '', description).strip()
            
            registry = project.get('registry', 'Unknown')
            project_type = project.get('type', 'Unknown')
            country = project.get('country', 'Unknown')
            methodology = project.get('methodology', '')
            status = project.get('status', '')
            registry_link = project.get('registry_link', '')
            
            # Create content
            content = f"Name: {name}\n\nRegistry: {registry}\nType: {project_type}\nCountry: {country}\nMethodology: {methodology}\nStatus: {status}\n\n{description}"
            
            # Create metadata
            metadata = {
                'name': name,
                'registry': registry,
                'type': project_type,
                'country': country,
                'methodology': methodology,
                'status': status,
                'registry_link': registry_link,
                'project_id': project_id,
                # Store the actual project ID from the original data
                'id': actual_project_id
            }
            
            # Split into chunks
            splits = self.text_splitter.split_text(content)
            for i, chunk in enumerate(splits):
                chunk_metadata = metadata.copy()
                chunk_metadata['chunk_index'] = i
                documents.append(Document(page_content=chunk, metadata=chunk_metadata))
        
        return documents
    
    def _initialize_vector_store(self):
        """Initialize or load the vector store."""
        if not LANGCHAIN_AVAILABLE or self.embeddings is None:
            return
        
        faiss_index_path = self.vector_store_path / "index.faiss"
        
        # Try to load existing vector store
        if faiss_index_path.exists():
            try:
                print(f"📂 Found existing vector store at: {self.vector_store_path}")
                logger.info("📂 Loading existing vector store...")
                
                # Set PyTorch to use float32 to avoid meta tensor issues
                import torch
                torch.set_default_dtype(torch.float32)
                
                self.vector_store = FAISS.load_local(
                    str(self.vector_store_path),
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                print(f"   ✓ Vector store loaded successfully")
                logger.info("✅ Vector store loaded")
                self._ready = True
                # Check for new projects and add them incrementally
                print("🔄 Checking for new projects...")
                self._add_new_projects()
                return
            except Exception as e:
                logger.warning(f"⚠️ Failed to load vector store: {e}")
                print(f"   ⚠️ Failed to load: {e}")
                print("   Will rebuild from scratch...")
                # Clean up corrupted vector store
                try:
                    import shutil
                    if self.vector_store_path.exists():
                        shutil.rmtree(self.vector_store_path)
                        print("   Cleaned up corrupted vector store")
                except Exception as cleanup_err:
                    logger.warning(f"Could not clean up: {cleanup_err}")
        else:
            print(f"   No existing vector store found")
        
        # Build initial vector store
        self._build_initial_vector_store()
        self._rebuild_bm25()
    
    def _build_initial_vector_store(self):
        """Build the vector store from scratch (first time only)."""
        with self._lock:
            print("=" * 70)
            print("🔨 BUILDING INITIAL VECTOR STORE")
            print("=" * 70)
            logger.info("🔨 Building initial vector store...")
            
            print("📂 Step 1/5: Loading projects from projects.jsonl...")
            MAX_PROJECTS = 1000
            projects = self._load_all_projects(limit=MAX_PROJECTS)
            if not projects:
                logger.warning("⚠️ No projects to index")
                return
            
            print(f"   ✓ Loaded {len(projects)} projects (limited to {MAX_PROJECTS} for RAG)")
            
            print(f"📝 Step 2/5: Creating document chunks...")
            documents = self._create_documents(projects)
            if not documents:
                logger.warning("⚠️ No documents created")
                return
            print(f"   ✓ Created {len(documents)} chunks")
            
            print(f"🤖 Step 3/5: Generating embeddings and building FAISS index...")
            print(f"   (This may take a few minutes for {len(documents)} chunks...)")
            # Create FAISS vector store in batches to prevent OOM
            self.vector_store = None
            batch_size = 100
            total_batches = (len(documents) - 1) // batch_size + 1
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i+batch_size]
                if self.vector_store is None:
                    self.vector_store = FAISS.from_documents(batch, self.embeddings)
                else:
                    self.vector_store.add_documents(batch)
                if (i // batch_size + 1) % 5 == 0 or (i // batch_size + 1) == total_batches:
                    print(f"   ✓ Embedded batch {i//batch_size + 1}/{total_batches}")
            print(f"   ✓ FAISS index built successfully")
            
            print(f"💾 Step 4/5: Saving vector store to disk...")
            # Save to disk
            self.vector_store_path.mkdir(parents=True, exist_ok=True)
            self.vector_store.save_local(str(self.vector_store_path))
            print(f"   ✓ Saved to {self.vector_store_path}")
            
            print(f"📋 Step 5/5: Updating indexed project IDs...")
            # Update indexed IDs
            for project in projects:
                self.indexed_ids.add(self._get_project_id(project))
            self._save_indexed_ids()
            print(f"   ✓ Saved {len(self.indexed_ids)} indexed IDs")
            
            print("=" * 70)
            print(f"✅ VECTOR STORE READY: {len(documents)} chunks from {len(projects)} projects")
            print("=" * 70)
            logger.info(f"✅ Initial vector store built with {len(documents)} chunks from {len(projects)} projects")
            self._ready = True
    
    def _add_new_projects(self):
        """Add only new projects to existing vector store (incremental update)."""
        if self.vector_store is None:
            return
        
        with self._lock:
            new_projects = self._get_new_projects()
            
            if not new_projects:
                return
            
            print("-" * 70)
            print(f"➕ INCREMENTAL UPDATE: Adding {len(new_projects)} new projects")
            print("-" * 70)
            logger.info(f"➕ Adding {len(new_projects)} new projects incrementally...")
            
            print(f"📝 Creating document chunks...")
            documents = self._create_documents(new_projects)
            if not documents:
                return
            print(f"   ✓ Created {len(documents)} new chunks")
            
            print(f"🤖 Generating embeddings and updating FAISS index...")
            # Add documents to existing vector store (incremental)
            self.vector_store.add_documents(documents)
            print(f"   ✓ Added to vector store")
            
            print(f"💾 Saving updated vector store...")
            # Save updated vector store
            self.vector_store.save_local(str(self.vector_store_path))
            print(f"   ✓ Saved to disk")
            
            print(f"📋 Updating indexed IDs...")
            # Update indexed IDs
            for project in new_projects:
                self.indexed_ids.add(self._get_project_id(project))
            self._save_indexed_ids()
            print(f"   ✓ Updated indexed IDs")
            
            print("-" * 70)
            logger.info(f"✅ Added {len(documents)} new chunks from {len(new_projects)} projects")
            
            # Rebuild BM25
            self._rebuild_bm25()
    
    def _check_and_update(self):
        """Background task: check for new projects and add them incrementally."""
        new_projects = self._get_new_projects()
        if new_projects:
            self._add_new_projects()
    
    def start_watching(self, interval: int = 60):
        """Start background thread to watch for projects.jsonl changes."""
        if self._watch_thread is not None:
            return
        
        self._stop_watching = False
        
        def watch_loop():
            while not self._stop_watching:
                try:
                    self._check_and_update()
                except Exception as e:
                    logger.error(f"Error in watch loop: {e}")
                time.sleep(interval)
        
        self._watch_thread = threading.Thread(target=watch_loop, daemon=True)
        self._watch_thread.start()
        logger.info(f"👁️ Started watching projects.jsonl (interval: {interval}s)")
    
    def stop_watching(self):
        """Stop the background watch thread."""
        self._stop_watching = True
        if self._watch_thread:
            self._watch_thread.join(timeout=5)
            self._watch_thread = None
    
    # ============================================================================
    # MAIN FUNCTION - RAG SEARCH
    # ============================================================================
    
    def search_projects(self, query: str, k: int = 5) -> List[Dict]:
        """
        Main function: Search for relevant project chunks using RAG.
        
        Args:
            query: Search query or question
            k: Number of chunks to return
            
        Returns:
            List of dicts with 'content', 'name', 'registry', 'registry_link', etc.
        """
        if self.vector_store is None:
            logger.warning("⚠️ Vector store not initialized")
            return []
        
        # 1. FAISS Search
        faiss_results = self.vector_store.similarity_search_with_score(query, k=k*3)
        
        # 2. BM25 Search
        bm25_results = []
        if self.bm25 and self.bm25_docs:
            tokenized_query = query.lower().split()
            bm25_scores = self.bm25.get_scores(tokenized_query)
            import numpy as np
            top_n = np.argsort(bm25_scores)[::-1][:k*3]
            bm25_results = [(self.bm25_docs[i], bm25_scores[i]) for i in top_n if bm25_scores[i] > 0]
            
        # 3. RRF Fusion
        if not bm25_results:
            results = faiss_results[:k]
        else:
            RRF_K = 60
            fused_scores = {}
            doc_map = {}
            
            faiss_results_sorted = sorted(faiss_results, key=lambda x: x[1])
            for rank, (doc, score) in enumerate(faiss_results_sorted):
                doc_id = doc.metadata.get('chunk_index', str(hash(doc.page_content)))
                key = f"{doc.metadata.get('id', 'unknown')}_{doc_id}"
                if key not in fused_scores:
                    fused_scores[key] = 0
                    doc_map[key] = doc
                fused_scores[key] += 1 / (RRF_K + rank + 1)
                
            bm25_results_sorted = sorted(bm25_results, key=lambda x: x[1], reverse=True)
            for rank, (doc, score) in enumerate(bm25_results_sorted):
                doc_id = doc.metadata.get('chunk_index', str(hash(doc.page_content)))
                key = f"{doc.metadata.get('id', 'unknown')}_{doc_id}"
                if key not in fused_scores:
                    fused_scores[key] = 0
                    doc_map[key] = doc
                fused_scores[key] += 1 / (RRF_K + rank + 1)
                
            sorted_fused = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
            results = [(doc_map[key], score) for key, score in sorted_fused[:k]]
        
        logger.info(f"🔍 Projects Hybrid RAG Search '{query}': found {len(results)} chunks")
        
        # Format results
        chunks = []
        for doc, score in results:
            chunks.append({
                'content': doc.page_content,
                'name': doc.metadata.get('name', ''),
                'registry': doc.metadata.get('registry', 'Unknown'),
                'registry_link': doc.metadata.get('registry_link', ''),
                'type': doc.metadata.get('type', 'Unknown'),
                'country': doc.metadata.get('country', 'Unknown'),
                'methodology': doc.metadata.get('methodology', ''),
                'status': doc.metadata.get('status', ''),
                'id': doc.metadata.get('id', ''),
                'metadata': doc.metadata,
                'score': float(score)
            })
        
        return chunks


# ============================================================================
# GLOBAL INSTANCE & PUBLIC API
# ============================================================================

_projects_rag_service: Optional[ProjectsRAGService] = None


def get_projects_rag_service() -> Optional[ProjectsRAGService]:
    """Get or create the global ProjectsRAGService instance."""
    global _projects_rag_service
    
    if _projects_rag_service is None:
        _projects_rag_service = ProjectsRAGService()
        _projects_rag_service.start_watching(interval=60)  # Check every minute
    
    return _projects_rag_service


def search_projects(query: str, k: int = 5) -> List[Dict]:
    """
    Main public function: Search projects using RAG.
    
    Args:
        query: Search query or question
        k: Number of chunks to return
        
    Returns:
        List of dicts with:
        - 'content': The text content
        - 'name': Project name
        - 'registry': Registry name
        - 'registry_link': URL to registry
        - 'type': Project type
        - 'country': Country
        - 'methodology': Methodology
        - 'status': Project status
        - 'id': Project ID
        - 'metadata': Full metadata dict
        - 'score': Similarity score
    
    Example:
        chunks = search_projects("renewable energy projects", k=3)
        for chunk in chunks:
            print(chunk['name'])
            print(chunk['registry'])
            print(chunk['registry_link'])
            print(chunk['content'])
    """
    service = get_projects_rag_service()
    if service:
        return service.search_projects(query, k=k)
    return []


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("🚀 Testing Projects RAG Service...")
    
    # Test search
    results = search_projects("tesla", k=3)
    
    print(f"\n📊 Found {len(results)} chunks:")
    for i, chunk in enumerate(results, 1):
        print(f"\n{i}. Score: {chunk['score']:.4f}")
        print(f"   Name: {chunk['name']}")
        print(f"   Registry: {chunk['registry']}")
        print(f"   Link: {chunk['registry_link']}")
        print(f"   Country: {chunk['country']}")
        print(f"   Content: {chunk['content'][:200]}...")
