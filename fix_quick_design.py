import re

# Read the file with UTF-8 encoding
with open(r"D:\SLD Design\src\app.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find and replace the corrupted _quick_design_page method
pattern = r"(    def _quick_design_page\(self\):.*?)(    def _design_analysis_page)"
replacement = r'''    def _quick_design_page(self):
        """Super streamlined quick design workflow"""
        st.markdown('<h1 class="main-header">🚀 Quick Electrical Design</h1>', unsafe_allow_html=True)
        st.markdown("Complete your electrical design in just a few clicks!")

        # Step 1: Choose design type
        st.markdown("### Step 1: Choose Your Design Type")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🏭 Manufacturing Plant", type="primary", use_container_width=True):
                st.session_state.quick_design_choice = "manufacturing"
                st.rerun()
        with col2:
            if st.button("🏢 Commercial Building", use_container_width=True):
                st.session_state.quick_design_choice = "commercial"
                st.rerun()
        with col3:
            if st.button("🏠 Residential Complex", use_container_width=True):
                st.session_state.quick_design_choice = "residential"
                st.rerun()

        design_choice = st.session_state.get("quick_design_choice")
        if design_choice:
            with st.spinner("Creating your project..."):
                self._create_template_project(design_choice)
                st.success(f"✅ {design_choice.title()} project created!")
                st.info("🔄 Running calculations...")
                self._perform_calculations()
                st.success("✅ Design complete!")
                st.balloons()

                # Show project summary when design is complete
                st.markdown("### 📊 Project Summary")

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Loads", len(self.project.loads))
                with col2:
                    total_power = sum(load.power_kw for load in self.project.loads)
                    st.metric("Total Power", f"{total_power:.1f} kW")
                with col3:
                    st.metric("Buses", len(self.project.buses))
                with col4:
                    st.metric("Transformers", len(self.project.transformers))

                # Load breakdown
                if self.project.loads:
                    st.markdown("#### Load Breakdown")
                    load_types = {}
                    for load in self.project.loads:
                        load_type = load.load_type.value
                        if load_type not in load_types:
                            load_types[load_type] = 0
                        load_types[load_type] += load.power_kw

                    for load_type, power in load_types.items():
                        st.write(f"• **{load_type.title()}**: {power:.1f} kW")

                # Quick actions
                st.markdown("### 🎉 Your Design is Ready!")
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("📊 View Results", type="primary", use_container_width=True):
                        st.session_state.selected_page = "📊 Design & Analysis"
                        if "quick_design_choice" in st.session_state:
                            del st.session_state.quick_design_choice
                        st.rerun()
                with col2:
                    if st.button("📥 Export All", use_container_width=True):
                        self._quick_export_all()
                        st.success("All reports exported!")
                with col3:
                    if st.button("🔄 Start New Design", use_container_width=True):
                        self._create_new_project()
                        if "quick_design_choice" in st.session_state:
                            del st.session_state.quick_design_choice
                        st.rerun()

    \2'''

fixed = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Write back
with open(r"D:\SLD Design\src\app.py", "w", encoding="utf-8") as f:
    f.write(fixed)

print("Fixed!")
