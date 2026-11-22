"""
nc_plotter_app - Streamlit web application for plotting .nc NetCDF files.

Key feature: Explicit variable selection - users can choose ANY variable
from the dataset, regardless of its name. No assumptions about parameter names.

This module provides a robust NetCDF plotter that handles common errors
in spatio-temporal datasets such as rainfall, temperature, and similar
CF-convention files.
"""
import os
import sys

# Resolve paths BEFORE changing directory: __file__ can be relative, and
# resolving it after os.chdir() would point at the wrong location.
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_APP_DIR)

# Change to this file's directory to handle paths with spaces issue
os.chdir(_APP_DIR)

for _path in (_PROJECT_ROOT, _APP_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
import pandas as pd

try:
    from nc_plotter_app.nc_utils import NetCDFHandler
    from nc_plotter_app.plotly_generator import PlotlyGenerator
    from nc_plotter_app.matplotlib_generator import MatplotlibGenerator
except ImportError:
    # Fallback when launched from inside the package directory.
    from nc_utils import NetCDFHandler
    from plotly_generator import PlotlyGenerator
    from matplotlib_generator import MatplotlibGenerator

# Page configuration
st.set_page_config(
    page_title="NetCDF Variable Plotter",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    .stFileUploader > div {border-width: 2px;}
    .stDownloadButton button {width: 100%;}
    .stWarning {background-color: #fff3e0; border-left: 4px solid #ff8f00;}
    .stInfo {background-color: #e3f2fd; border: 1px solid #90caf9; border-radius: 5px; padding: 10px;}
    </style>
""", unsafe_allow_html=True)

st.title("🌊 NetCDF Variable Plotter")
st.markdown("**Upload a NetCDF file** and explicitly select which variable to plot. Works with any variable name.")

# Sidebar - File Upload
st.sidebar.header("📁 File Upload")
uploaded_file = st.sidebar.file_uploader(
    "Choose a NetCDF file (.nc)",
    type=["nc"],
    help="Upload any CF-compliant NetCDF file. All variables will be listed for selection."
)

if uploaded_file is not None:
    # Load dataset with error handling
    with st.spinner("Loading NetCDF dataset and extracting variables..."):
        try:
            ds = NetCDFHandler.load_dataset(uploaded_file)
            st.sidebar.success("✅ Dataset loaded successfully!")
        except Exception as e:
            st.sidebar.error(f"❌ Failed to load dataset: {str(e)}")
            st.stop()

    # Get ALL variable info from dataset
    try:
        var_info = NetCDFHandler.get_variable_info(ds)
        all_var_names = [v["name"] for v in var_info]
    except Exception as e:
        st.sidebar.error(f"❌ Error extracting variable info: {str(e)}")
        st.stop()

    # ==========================================
    # EXPLICIT VARIABLE SELECTION (KEY FEATURE)
    # ==========================================

    st.sidebar.header("🔍 Select Variable to Plot")
    st.sidebar.caption(f"Total variables in dataset: {len(var_info)}")

    with st.sidebar.expander("View All Variables", expanded=True):
        selected_var = None
        cols = st.columns(2)
        for idx, var_name in enumerate(all_var_names):
            col = cols[idx % 2]
            with col:
                try:
                    var_detail = next(v for v in var_info if v["name"] == var_name)
                    units = var_detail.get("units", "")
                    long_name = var_detail.get("long_name", var_name)
                    dims = var_detail.get("dims", "")
                    shape = var_detail.get("shape", "")
                    st.markdown(f"**📦 {var_name}**")
                    st.caption(f"Long name: {long_name} | Units: {units if units else 'None'} | Dims: {dims} | Shape: {shape}")
                    is_selected = st.checkbox("Select", key=f"select_{var_name}")
                    if is_selected and selected_var is None:
                        selected_var = var_name
                    elif is_selected and selected_var == var_name:
                        pass
                    elif is_selected and selected_var != var_name:
                        selected_var = var_name
                except Exception as e:
                    st.error(f"Error displaying {var_name}: {str(e)}")

    # Critical: stop if no variable selected
    if selected_var is None:
        st.info("👈 Please select a variable from the sidebar to begin exploring.")
        st.stop()

    # Show selected variable details
    try:
        var_detail = next(v for v in var_info if v["name"] == selected_var)
        selected_units = var_detail.get("units", "")
        selected_long_name = var_detail.get("long_name", selected_var)
        selected_dims = var_detail.get("dims", "")
        selected_shape = var_detail.get("shape", "")

        st.sidebar.success(f"✅ Selected: **{selected_var}**")
        st.sidebar.caption(f"Long name: {selected_long_name}")
        if selected_units:
            st.sidebar.caption(f"Units: {selected_units}")
        st.sidebar.caption(f"Dimensions: {selected_dims}")
        st.sidebar.caption(f"Shape: {selected_shape}")
    except Exception as e:
        st.sidebar.error(f"Error showing variable details: {str(e)}")
        st.stop()

    # Optional comparison variable
    comparison_var = None
    if len(all_var_names) > 1:
        with st.sidebar.expander("Select Comparison Variable"):
            for var_name in all_var_names:
                if var_name != selected_var:
                    if st.checkbox(var_name, key=f"compare_{var_name}", help=f"Compare with {selected_var}"):
                        comparison_var = var_name
                        st.sidebar.success(f"Comparison variable: {var_name}")
    else:
        st.sidebar.info("Only one variable in dataset.")

    # Plot type selection
    plot_type = st.sidebar.radio("Choose plot type", ["Plotly Interactive", "Matplotlib Static"],
        help="Plotly: interactive zooming, panning, tooltips. Matplotlib: publication-quality static plots.")

    plot_ds = ds

    if plot_type == "Plotly Interactive":
        plot_subtype = st.sidebar.radio("Plot type", ["Time Series", "Contour Map", "3D Surface", "Animation"])

        # Time range selection
        time_range_plot = None
        if plot_subtype == "Time Series" and "time" in ds.coords:
            try:
                time_range_plot = st.sidebar.slider("Time range", 0, max(1, ds.sizes["time"] - 1),
                    value=(0, min(5, ds.sizes["time"] - 1)),
                    help="Select the time range to display")
            except Exception as e:
                st.sidebar.warning(f"Time range error: {str(e)}")
                time_range_plot = None

        # Spatial subsetting
        use_spatial = st.sidebar.checkbox("Spatial subsetting (lat/lon range)", value=False)
        lat_range = lon_range = None
        if use_spatial and "lat" in ds.coords and "lon" in ds.coords:
            try:
                lat_range = st.sidebar.slider("Latitude range", float(ds.coords["lat"].min()),
                    float(ds.coords["lat"].max()),
                    value=(float(ds.coords["lat"].min()), float(ds.coords["lat"].max())))
                lon_range = st.sidebar.slider("Longitude range", float(ds.coords["lon"].min()),
                    float(ds.coords["lon"].max()),
                    value=(float(ds.coords["lon"].min()), float(ds.coords["lon"].max())))
            except Exception as e:
                st.sidebar.warning(f"Spatial subsetting error: {str(e)}")
                use_spatial = False

        if use_spatial and lat_range is not None and lon_range is not None:
            try:
                plot_ds = ds.sel(lat=slice(lat_range[0], lat_range[1]), lon=slice(lon_range[0], lon_range[1]))
            except Exception as e:
                st.sidebar.warning(f"Spatial subsetting error: {str(e)}")
                plot_ds = ds

        if plot_subtype == "Time Series":
            try:
                fig = PlotlyGenerator.plot_timeseries(plot_ds, selected_var, time_range_plot)
                st.plotly_chart(fig, width='stretch')
                fig.write_json("plot_data.json")
                st.download_button("Download plot data as JSON", data=open("plot_data.json", "rb").read(),
                    file_name="plot_data.json", mime="application/json")
                if os.path.exists("plot_data.json"): os.remove("plot_data.json")
            except Exception as e:
                st.error(f"Error generating time series plot: {str(e)}")

        elif plot_subtype == "Contour Map":
            try:
                time_idx = st.sidebar.slider("Time step", 0, plot_ds.sizes["time"] - 1, 0) \
                    if "time" in plot_ds.coords and plot_ds.sizes["time"] > 1 else None
                fig = PlotlyGenerator.plot_contour_map(plot_ds, selected_var, time_idx=time_idx)
                var_units = var_detail.get("units", "")
                var_long_name = var_detail.get("long_name", selected_var)
                title = f"{var_long_name}" + (f" ({var_units})" if var_units else "")
                fig.update_layout(title=title)
                st.plotly_chart(fig, width='stretch')
                fig.write_json(f"plot_data_{selected_var}.json")
                st.download_button(f"Download {selected_var} plot data as JSON",
                    data=open(f"plot_data_{selected_var}.json", "rb").read(),
                    file_name=f"plot_data_{selected_var}.json", mime="application/json")
                if os.path.exists(f"plot_data_{selected_var}.json"): os.remove(f"plot_data_{selected_var}.json")
            except Exception as e:
                st.error(f"Error generating contour map: {str(e)}")

        elif plot_subtype == "3D Surface":
            try:
                time_idx = st.sidebar.slider("Time step for 3D surface", 0, plot_ds.sizes["time"] - 1, 0) \
                    if "time" in plot_ds.coords and plot_ds.sizes["time"] > 1 else None
                fig = PlotlyGenerator.plot_3d_surface(plot_ds, selected_var, time_idx=time_idx)
                var_units = var_detail.get("units", "")
                var_long_name = var_detail.get("long_name", selected_var)
                title = f"{var_long_name}" + (f" ({var_units})" if var_units else "")
                fig.update_layout(title=title)
                st.plotly_chart(fig, width='stretch')
            except Exception as e:
                st.error(f"Error generating 3D surface: {str(e)}")

        elif plot_subtype == "Animation":
            try:
                fig = PlotlyGenerator.plot_animation(plot_ds, selected_var)
                st.plotly_chart(fig, width='stretch')
            except Exception as e:
                st.error(f"Error generating animation: {str(e)}")

    else:  # Matplotlib Static
        plot_subtype = st.sidebar.radio("Plot type", ["Contour Map", "Time Series", "Rainfall Distribution"])

        var_units = selected_units
        var_long_name = selected_long_name

        # Time index selection
        time_idx = st.sidebar.slider("Time step", 0, plot_ds.sizes["time"] - 1, 0) \
            if "time" in plot_ds.coords and plot_ds.sizes["time"] > 1 else None

        # Spatial subsetting
        use_spatial = st.sidebar.checkbox("Spatial subsetting (lat/lon range)", value=False)
        lat_range = lon_range = None
        if use_spatial and "lat" in plot_ds.coords and "lon" in plot_ds.coords:
            try:
                lat_range = st.sidebar.slider("Latitude range", float(plot_ds.coords["lat"].min()),
                    float(plot_ds.coords["lat"].max()),
                    value=(float(plot_ds.coords["lat"].min()), float(plot_ds.coords["lat"].max())))
                lon_range = st.sidebar.slider("Longitude range", float(plot_ds.coords["lon"].min()),
                    float(plot_ds.coords["lon"].max()),
                    value=(float(plot_ds.coords["lon"].min()), float(plot_ds.coords["lon"].max())))
                plot_ds = plot_ds.sel(lat=slice(lat_range[0], lat_range[1]), lon=slice(lon_range[0], lon_range[1]))
            except Exception as e:
                st.sidebar.warning(f"Spatial subsetting error: {str(e)}")

        # Sanitize data
        try:
            plot_var = plot_ds[selected_var]
            plot_var_sanitized = NetCDFHandler.sanitize_data(plot_var)
        except Exception as e:
            st.error(f"Error sanitizing data: {str(e)}")
            st.stop()

        if plot_subtype == "Contour Map":
            try:
                with st.spinner("Generating contour map..."):
                    fig, ax = MatplotlibGenerator.plot_contourf_map(plot_ds, selected_var, time_idx=time_idx)
                    var_units = var_detail.get("units", "")
                    var_long_name = var_detail.get("long_name", selected_var)
                    fig.suptitle(f"{var_long_name}\n({var_units})" if var_units else var_long_name, fontsize=12)
                    fig.savefig("contour_plot.png", dpi=150, bbox_inches='tight')
                    st.pyplot(fig)
                    plt.close(fig)
                    st.download_button("Download plot as PNG", data=open("contour_plot.png", "rb").read(),
                        file_name="contour_plot.png", mime="image/png")
                if os.path.exists("contour_plot.png"): os.remove("contour_plot.png")
            except Exception as e:
                st.error(f"Error generating contour map: {str(e)}")

        elif plot_subtype == "Time Series":
            try:
                with st.spinner("Generating time series..."):
                    fig, ax = MatplotlibGenerator.plot_timeseries(plot_ds, selected_var)
                    var_units = var_detail.get("units", "")
                    fig.suptitle(f"{var_long_name}\n({var_units})" if var_units else var_long_name, fontsize=14)
                    fig.savefig("timeseries_plot.png", dpi=150, bbox_inches='tight')
                    st.pyplot(fig)
                    plt.close(fig)
                    st.download_button("Download plot as PNG", data=open("timeseries_plot.png", "rb").read(),
                        file_name="timeseries_plot.png", mime="image/png")
                if os.path.exists("timeseries_plot.png"): os.remove("timeseries_plot.png")
            except Exception as e:
                st.error(f"Error generating time series: {str(e)}")

        elif plot_subtype == "Rainfall Distribution":
            try:
                with st.spinner("Generating distribution plot..."):
                    fig, ax = MatplotlibGenerator.plot_rainfall_distribution(plot_ds, selected_var)
                    var_units = var_detail.get("units", "")
                    fig.suptitle(f"Distribution: {var_long_name}\n({var_units})" if var_units else f"Distribution: {var_long_name}", fontsize=14)
                    fig.savefig("distribution_plot.png", dpi=150, bbox_inches='tight')
                    st.pyplot(fig)
                    plt.close(fig)
                    st.download_button("Download plot as PNG", data=open("distribution_plot.png", "rb").read(),
                        file_name="distribution_plot.png", mime="image/png")
                if os.path.exists("distribution_plot.png"): os.remove("distribution_plot.png")
            except Exception as e:
                st.error(f"Error generating distribution plot: {str(e)}")

else:
    # Welcome screen
    st.info("👈 Please upload a NetCDF file from the sidebar to begin exploring.")
    st.markdown("""
    **How it works:**
    1. **Upload** any .nc file - the app lists ALL variables automatically
    2. **Select** exactly which variable you want to plot (by name, units, or dimension layout)
    3. **Choose** plot type: Interactive (Plotly) or Static (Matplotlib)
    4. **Adjust** time range and spatial subsetting if desired
    5. **View** and **Download** your plot

    **This works with ANY variable name:**
    - `rainfall`, `precip`, `pr`, `rr` - all work
    - `t2m`, `tas`, `temp`, `air_temp` - all work
    - `u10`, `v10`, `wind`, `wspd` - all work
    - `sst`, `sea_surface_temp` - all work
    - Or any custom variable name your dataset uses

    **The app automatically:**
    - Detects the variable's dimensions and shape
    - Handles fill values (-999, 9.96921e+36, etc.)
    - Parses time units (hours/days since epoch)
    - Validates lat/lon coordinates
    - Sanitizes data for plotting
    """)

st.sidebar.markdown("---")
st.sidebar.caption("NetCDF Variable Plotter App • Built with Streamlit, Xarray, Plotly & Matplotlib")