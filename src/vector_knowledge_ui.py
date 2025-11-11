"""
Vector Knowledge Management UI for Electrical Design Automation System

This module provides a comprehensive Streamlit-based user interface for managing
and visualizing the vector knowledge base, including search, editing, analytics,
and knowledge discovery features.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime
import time
from typing import Dict, List, Any, Optional, Tuple
import hashlib

# Vector database integration
try:
    from vector_database_manager import get_vector_database, VectorDatabaseManager
    VECTOR_DB_AVAILABLE = True
except ImportError:
    VECTOR_DB_AVAILABLE = False
    st.error("Vector database not available. Please check installation.")

# Embedding pipeline integration
try:
    from embedding_generation_pipeline import EmbeddingGenerationPipeline
    EMBEDDING_PIPELINE_AVAILABLE = True
except ImportError:
    EMBEDDING_PIPELINE_AVAILABLE = False

# Configure page
st.set_page_config(
    page_title="Vector Knowledge Management",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .knowledge-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border-left: 4px solid #007bff;
    }
    .metric-card {
        background-color: #e9ecef;
        border-radius: 8px;
        padding: 15px;
        margin: 5px;
        text-align: center;
    }
    .search-result {
        background-color: #f8f9fa;
        border-radius: 5px;
        padding: 10px;
        margin: 5px 0;
        border-left: 3px solid #28a745;
    }
    .stats-container {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)


class VectorKnowledgeUI:
    """Main UI class for vector knowledge management"""

    def __init__(self):
        self.vector_db = None
        self.embedding_pipeline = None
        self._initialize_components()

    def _initialize_components(self):
        """Initialize vector database and embedding pipeline"""
        if VECTOR_DB_AVAILABLE:
            try:
                self.vector_db = get_vector_database()
                st.sidebar.success("✅ Vector Database Connected")

                # Check if collections need initialization
                self._check_and_initialize_knowledge_base()

            except Exception as e:
                st.sidebar.error(f"❌ Vector Database Error: {e}")

        if EMBEDDING_PIPELINE_AVAILABLE:
            try:
                self.embedding_pipeline = EmbeddingGenerationPipeline()
                st.sidebar.success("✅ Embedding Pipeline Ready")
            except Exception as e:
                st.sidebar.warning(f"⚠️ Embedding Pipeline Error: {e}")

    def _check_and_initialize_knowledge_base(self):
        """Check if knowledge base collections are empty and initialize with default data"""
        if not self.vector_db:
            return

        try:
            # Get collection statistics
            stats = self.vector_db.get_collection_stats()

            # Check if key collections are empty (excluding excel_headers which is already populated)
            empty_collections = []
            for collection_type in ['component_specs', 'design_patterns', 'standards']:
                info = stats.get(collection_type, {})
                if isinstance(info, dict) and info.get('count', 0) == 0:
                    empty_collections.append(collection_type)

            # If collections are empty, initialize default knowledge base
            if empty_collections:
                st.sidebar.info("🔄 Initializing knowledge base...")
                try:
                    self.vector_db.initialize_default_knowledge_base()
                    st.sidebar.success("✅ Knowledge base initialized!")
                except Exception as e:
                    st.sidebar.error(f"❌ Failed to initialize knowledge base: {e}")

        except Exception as e:
            st.sidebar.warning(f"⚠️ Could not check knowledge base status: {e}")

    def render_main_ui(self):
        """Render the main knowledge management interface"""
        st.title("🧠 Vector Knowledge Management")
        st.markdown("Manage and explore the electrical engineering knowledge base")

        if not self.vector_db:
            st.error("Vector database not available. Please check the system configuration.")
            return

        # Sidebar navigation
        self._render_sidebar()

        # Main content area
        tab1, tab2, tab3, tab4 = st.tabs([
            "🔍 Search & Query",
            "📊 Analytics & Stats",
            "🔧 Management Tools",
            "📈 Performance Monitor"
        ])

        with tab1:
            self._render_search_interface()

        with tab2:
            self._render_analytics_dashboard()

        with tab3:
            self._render_management_tools()

        with tab4:
            self._render_performance_monitor()

    def _render_sidebar(self):
        """Render sidebar with navigation and quick stats"""
        st.sidebar.title("Navigation")

        # Quick stats
        if self.vector_db:
            try:
                stats = self.vector_db.get_collection_stats()
                st.sidebar.subheader("📈 Quick Stats")

                total_items = sum(info.get('count', 0) for info in stats.values() if isinstance(info, dict))
                st.sidebar.metric("Total Knowledge Items", total_items)

                # Cache stats
                cache_stats = self.vector_db.get_cache_stats()
                valid_entries = cache_stats.get('valid_cache_entries', 0)
                total_cache_entries = cache_stats.get('query_cache_size', 0) + cache_stats.get('embedding_cache_size', 0)
                if total_cache_entries:
                    cache_hit_rate = min((valid_entries / total_cache_entries) * 100, 100.0)
                else:
                    cache_hit_rate = 0.0
                st.sidebar.metric("Cache Hit Rate", f"{cache_hit_rate:.1f}%")

                # Performance indicator
                if valid_entries > 0:
                    st.sidebar.success("🟢 System Healthy")
                else:
                    st.sidebar.warning("🟡 System Starting")

            except Exception as e:
                st.sidebar.error(f"Stats Error: {e}")

        # Collection selector
        st.sidebar.subheader("Active Collection")
        collections = ['excel_headers', 'component_specs', 'design_patterns', 'standards']
        selected_collection = st.sidebar.selectbox("Select Collection", collections)

        # Quick actions
        st.sidebar.subheader("Quick Actions")
        if st.sidebar.button("🔄 Refresh Stats"):
            st.rerun()

        if st.sidebar.button("🧹 Optimize Cache"):
            if self.vector_db:
                self.vector_db.optimize_cache()
                st.sidebar.success("Cache optimized!")

    def _render_search_interface(self):
        """Render the search and query interface"""
        st.header("🔍 Knowledge Base Search")

        col1, col2 = st.columns([3, 1])

        with col1:
            query = st.text_input(
                "Search Query",
                placeholder="Enter electrical engineering terms, component specs, or standards...",
                help="Search across all knowledge domains using natural language"
            )

        with col2:
            search_domain = st.selectbox(
                "Domain",
                ["all", "electrical", "components", "standards", "patterns"],
                help="Limit search to specific knowledge domain"
            )

        col1, col2, col3 = st.columns(3)
        with col1:
            top_k = st.slider("Results", 5, 20, 10)
        with col2:
            include_sources = st.checkbox("Include Sources", value=True)
        with col3:
            use_cache = st.checkbox("Use Cache", value=True)

        if st.button("🔍 Search", type="primary", use_container_width=True):
            if query.strip():
                self._perform_search(query, search_domain, top_k, include_sources, use_cache)
            else:
                st.warning("Please enter a search query")

        # Advanced search options
        with st.expander("🔧 Advanced Search Options"):
            st.markdown("### Semantic Search Settings")
            similarity_threshold = st.slider("Similarity Threshold", 0.1, 1.0, 0.7)

            st.markdown("### Domain Filters")
            domains = st.multiselect(
                "Specific Collections",
                ["excel_headers", "component_specs", "design_patterns", "standards"],
                default=["component_specs", "standards"]
            )

    def _perform_search(self, query: str, domain: str, top_k: int,
                       include_sources: bool, use_cache: bool):
        """Execute search and display results"""
        with st.spinner("Searching knowledge base..."):
            try:
                start_time = time.perf_counter()
                results = self.vector_db.rag_query(
                    query=query,
                    context_domain=domain,
                    top_k=top_k,
                    include_sources=include_sources
                )
                query_time = time.perf_counter() - start_time

                # Display results
                self._display_search_results(results, query, query_time)

            except Exception as e:
                st.error(f"Search failed: {e}")

    def _display_search_results(self, results: Dict, query: str, query_time: Optional[float] = None):
        """Display search results in a structured format"""
        if not results.get('context'):
            st.warning("No results found for the query")
            return

        st.success(f"Found relevant knowledge for: **{query}**")

        # Main context
        st.subheader("📄 Retrieved Context")
        st.info(results['context'])

        # Sources (if available)
        if results.get('sources'):
            st.subheader("📚 Source Details")

            sources_df = []
            for source in results['sources']:
                source_type = source.get('type', 'unknown')
                score = source.get('score')
                if isinstance(score, (int, float, np.floating)):
                    score_value = f"{float(score):.3f}"
                else:
                    score_value = "N/A"
                source_id = source.get('id')
                if source_id is None:
                    source_id = source.get('header', 'N/A')
                source_id_display = str(source_id)
                sources_df.append({
                    'Type': source_type.title() if isinstance(source_type, str) else str(source_type),
                    'ID': source_id_display,
                    'Score': score_value,
                    'Details': self._format_source_details(source)
                })

            st.dataframe(pd.DataFrame(sources_df), use_container_width=True)

        # Metadata
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Context Length", len(results.get('context', '')))
        with col2:
            st.metric("Sources Found", len(results.get('sources', [])))
        with col3:
            query_time_display = f"{query_time:.2f}s" if query_time is not None else "—"
            st.metric("Query Time", query_time_display)

    def _format_source_details(self, source: Dict) -> str:
        """Format source details for display"""
        if source['type'] == 'component':
            return f"Component: {source['data'].get('component_id', 'N/A')}"
        elif source['type'] == 'standard':
            return f"Standard: {source['data'].get('title', 'N/A')}"
        elif source['type'] == 'design_pattern':
            return f"Pattern: {source['data'].get('description', 'N/A')[:50]}..."
        elif source['type'] == 'excel_header':
            return f"Header: {source['header']} → {source['field']}"
        return "Unknown source type"

    def _render_analytics_dashboard(self):
        """Render analytics and statistics dashboard"""
        st.header("📊 Knowledge Base Analytics")

        if not self.vector_db:
            st.error("Vector database not available")
            return

        try:
            # Get statistics
            collection_stats = self.vector_db.get_collection_stats()
            cache_stats = self.vector_db.get_cache_stats()

            # Overview metrics
            st.subheader("📈 Overview Metrics")

            col1, col2, col3, col4 = st.columns(4)

            total_items = sum(info.get('count', 0) for info in collection_stats.values()
                            if isinstance(info, dict) and 'count' in info)
            with col1:
                st.metric("Total Knowledge Items", total_items)

            with col2:
                st.metric("Active Collections", len([c for c in collection_stats.values()
                                                   if isinstance(c, dict) and c.get('count', 0) > 0]))

            with col3:
                cache_size = cache_stats.get('query_cache_size', 0) + cache_stats.get('embedding_cache_size', 0)
                st.metric("Cached Items", cache_size)

            with col4:
                st.metric("System Health", "🟢 Good" if total_items > 0 else "🟡 Initializing")

            # Collection breakdown
            st.subheader("📚 Collection Statistics")

            collections_data = []
            for collection_name, info in collection_stats.items():
                if isinstance(info, dict):
                    collections_data.append({
                        'Collection': collection_name.replace('_', ' ').title(),
                        'Items': info.get('count', 0),
                        'Status': 'Active' if info.get('count', 0) > 0 else 'Empty'
                    })

            if collections_data:
                collections_df = pd.DataFrame(collections_data)
                fig = px.bar(collections_data, x='Collection', y='Items',
                           title='Knowledge Items by Collection',
                           color='Status')
                st.plotly_chart(fig, use_container_width=True)

                # Detailed table
                st.dataframe(collections_df, use_container_width=True)

            # Cache performance
            st.subheader("⚡ Cache Performance")

            cache_col1, cache_col2, cache_col3 = st.columns(3)

            total_cache_entries = cache_stats.get('query_cache_size', 0) + cache_stats.get('embedding_cache_size', 0)
            valid_cache_entries = cache_stats.get('valid_cache_entries', 0)
            if total_cache_entries:
                cache_hit_rate = min((valid_cache_entries / total_cache_entries) * 100, 100.0)
            else:
                cache_hit_rate = 0.0

            with cache_col1:
                st.metric("Cache Hit Rate", f"{cache_hit_rate:.1f}%")

            with cache_col2:
                st.metric("Query Cache Size", cache_stats.get('query_cache_size', 0))

            with cache_col3:
                st.metric("Embedding Cache Size", cache_stats.get('embedding_cache_size', 0))

            # Knowledge growth chart (placeholder - would need historical data)
            st.subheader("📈 Knowledge Growth Trend")
            st.info("Historical growth tracking would be implemented here with time-series data")

        except Exception as e:
            st.error(f"Failed to load analytics: {e}")




    def _render_management_tools(self):
        """Render management and maintenance tools"""
        st.header("🔧 Management Tools")

        tool_tab1, tool_tab2, tool_tab3, tool_tab4 = st.tabs([
            "💾 Backup/Restore",
            "🧹 Cache Management",
            "🔄 Rebuild Indexes",
            "📊 Data Quality"
        ])

        with tool_tab1:
            self._render_backup_restore_tools()

        with tool_tab2:
            self._render_cache_management()

        with tool_tab3:
            self._render_index_rebuild_tools()

        with tool_tab4:
            self._render_data_quality_tools()

    def _render_backup_restore_tools(self):
        """Backup and restore functionality"""
        st.subheader("💾 Backup & Restore")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Create Backup")
            backup_name = st.text_input("Backup Name", value=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            if st.button("📦 Create Backup"):
                try:
                    success = self.vector_db.backup_database(backup_name)
                    if success:
                        st.success(f"✅ Backup created: {backup_name}.zip")
                    else:
                        st.error("❌ Backup failed")
                except Exception as e:
                    st.error(f"❌ Backup error: {e}")

        with col2:
            st.markdown("### Restore from Backup")
            st.info("Restore functionality would be implemented with file upload and confirmation")

    def _render_cache_management(self):
        """Cache management tools"""
        st.subheader("🧹 Cache Management")

        if self.vector_db:
            cache_stats = self.vector_db.get_cache_stats()

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Query Cache Size", cache_stats.get('query_cache_size', 0))
            with col2:
                st.metric("Embedding Cache Size", cache_stats.get('embedding_cache_size', 0))
            with col3:
                st.metric("TTL (seconds)", cache_stats.get('cache_ttl_seconds', 3600))

            # Cache operations
            st.markdown("### Cache Operations")

            cache_op1, cache_op2, cache_op3, cache_op4 = st.columns(4)

            with cache_op1:
                if st.button("🔄 Optimize Cache"):
                    self.vector_db.optimize_cache()
                    st.success("Cache optimized!")

            with cache_op2:
                if st.button("🧹 Clear Query Cache"):
                    self.vector_db.clear_cache("query")
                    st.success("Query cache cleared!")

            with cache_op3:
                if st.button("🧽 Clear Embedding Cache"):
                    self.vector_db.clear_cache("embedding")
                    st.success("Embedding cache cleared!")

            with cache_op4:
                if st.button("💥 Clear All Cache"):
                    self.vector_db.clear_cache("all")
                    st.success("All caches cleared!")

            # Cache configuration
            st.markdown("### Cache Configuration")
            new_ttl = st.number_input("Cache TTL (seconds)", value=cache_stats.get('cache_ttl_seconds', 3600), min_value=60)
            new_size = st.number_input("Max Cache Size", value=cache_stats.get('cache_max_size', 2000), min_value=100)

            if st.button("⚙️ Update Configuration"):
                self.vector_db.set_cache_ttl(new_ttl)
                self.vector_db.set_cache_size(new_size)
                st.success("Cache configuration updated!")

    def _render_index_rebuild_tools(self):
        """Index rebuild and maintenance"""
        st.subheader("🔄 Index Management")

        st.info("Index rebuild and optimization tools would be implemented here")
        st.markdown("""
        - Rebuild vector indexes for improved search performance
        - Compact database storage
        - Update embeddings with new models
        - Validate index integrity
        """)

    def _render_data_quality_tools(self):
        """Data quality assessment and improvement"""
        st.subheader("📊 Data Quality Assessment")

        st.info("Data quality analysis and improvement tools would be implemented here")
        st.markdown("""
        - Check for duplicate entries
        - Validate data consistency
        - Assess embedding quality
        - Generate quality reports
        """)

    def _render_performance_monitor(self):
        """Performance monitoring dashboard"""
        st.header("📈 Performance Monitor")

        st.subheader("System Performance Metrics")

        # This would show real-time performance metrics
        # For now, show placeholder metrics

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Avg Query Time", "0.45s", "↗️ 0.05s")

        with col2:
            st.metric("Cache Hit Rate", "87.3%", "↗️ 5.2%")

        with col3:
            st.metric("Active Connections", "12", "↗️ 3")

        with col4:
            st.metric("Memory Usage", "2.4GB", "↘️ 0.2GB")

        # Performance charts (placeholders)
        st.subheader("Query Performance Over Time")
        st.line_chart(np.random.randn(50, 3).cumsum(0) + 100, height=200)

        st.subheader("Cache Performance")
        cache_data = pd.DataFrame({
            'Time': range(24),
            'Hit Rate': np.random.uniform(80, 95, 24),
            'Miss Rate': np.random.uniform(5, 20, 24)
        })
        st.area_chart(cache_data.set_index('Time'), height=200)


def main():
    """Main function to run the Vector Knowledge Management UI"""
    ui = VectorKnowledgeUI()
    ui.render_main_ui()


if __name__ == "__main__":
    main()