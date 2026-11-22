"""
plotly_generator.py - Interactive Plotly plots for spatio-temporal NetCDF data.

Provides interactive plotting using Plotly for exploring gridded rainfall, temperature,
and similar CF-convention datasets. Handles NaN values, units labeling, and interactive
features like zooming, panning, and tooltips.
"""

import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import xarray as xr

try:
    from .nc_utils import NetCDFHandler
except ImportError:  # Allow importing this module directly
    from nc_utils import NetCDFHandler


class PlotlyGenerator:
    """Generate interactive Plotly plots for NetCDF data."""

    @staticmethod
    def plot_timeseries(ds, var_name, time_range=None):
        """
        Create an interactive time series plot for a variable.

        Parameters
        ----------
        ds : xr.Dataset
            The NetCDF dataset
        var_name : str
            Name of the variable to plot
        time_range : tuple, optional
            (start, end) strings to filter the time axis

        Returns
        -------
        plotly.graph_objects.Figure
            Interactive time series figure
        """
        import pandas as pd

        # Get the variable
        if var_name not in ds.data_vars:
            raise ValueError(f"Variable {var_name} not found in dataset")

        var = ds[var_name]

        # Apply time range filter if specified
        if time_range and "time" in ds.coords:
            start, end = time_range
            if isinstance(start, (int, np.integer)) and isinstance(end, (int, np.integer)):
                # The app's slider supplies positional indices rather than dates.
                var = var.isel(time=slice(int(start), int(end) + 1))
            else:
                dt_idx = NetCDFHandler.parse_time(ds)
                if dt_idx is not None:
                    mask = (dt_idx >= start) & (dt_idx <= end)
                    var = var.sel(time=mask)

        # Sanitize data
        var = NetCDFHandler.sanitize_data(var)

        # Compute mean over spatial dimensions for timeseries
        if "lat" in var.dims and "lon" in var.dims:
            ts = var.mean(dim=["lat", "lon"])
        elif "lat" in var.dims:
            ts = var.mean(dim="lat")
        elif "lon" in var.dims:
            ts = var.mean(dim="lon")
        else:
            ts = var

        # Convert to pandas
        ts_pd = ts.to_pandas()

        # Handle NaN values
        ts_pd = ts_pd.dropna()

        if len(ts_pd) == 0:
            # Create empty figure with message
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for the selected time range",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig

        # Create time series plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=ts_pd.index,
            y=ts_pd.values,
            mode='lines+markers',
            line=dict(color='royalblue', width=2),
            marker=dict(size=4, color='lightseagreen'),
            hovertemplate='%{x}: %{y}<extra></extra>'
        ))

        # Update layout
        var_units = var.attrs.get("units", "")
        var_long_name = var.attrs.get("long_name", var_name)

        title = f"{var_long_name}"
        if var_units:
            title += f" ({var_units})"

        fig.update_layout(
            title=title,
            xaxis_title="Time",
            yaxis_title=f"Value {var_units if var_units else ''}".strip(),
            hovermode='x unified',
            template="plotly_white",
            width=800,
            height=450,
            margin=dict(l=50, r=50, t=50, b=50),
        )

        # Add grid
        fig.update_xaxes(gridwidth=1, gridcolor='lightgray')
        fig.update_yaxes(gridwidth=1, gridcolor='lightgray')

        return fig

    @staticmethod
    def plot_contour_map(ds, var_name, time_idx=None, levels=None):
        """
        Create an interactive contour map for a variable at a given time index.

        Parameters
        ----------
        ds : xr.Dataset
            The NetCDF dataset
        var_name : str
            Name of the variable to plot
        time_idx : int, optional
            Index into the time dimension. If None, uses the middle time step.
        levels : list, optional
            Contour levels. If None, auto-generated.

        Returns
        -------
        plotly.graph_objects.Figure
            Interactive contour map figure
        """
        import numpy as np

        # Get the variable
        if var_name not in ds.data_vars:
            raise ValueError(f"Variable {var_name} not found in dataset")

        var = ds[var_name]

        # Apply time index selection
        if time_idx is not None:
            var = var.isel(time=time_idx)

        # Sanitize data
        var = NetCDFHandler.sanitize_data(var)

        # Get data values, replacing NaN with minimum for coloring
        z = var.values.copy()
        if np.all(np.isnan(z)):
            # All values are NaN
            fig = go.Figure()
            fig.add_annotation(
                text="No valid data available for this selection",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig

        # Replace NaN with minimum for color scaling (but keep track)
        z_min = np.nanmin(z) if not np.all(np.isnan(z)) else 0
        z_max = np.nanmax(z)

        # Create mask for NaN
        nan_mask = np.isnan(z)

        # If all values are valid, use full range
        if np.all(~nan_mask):
            z_min = float(np.min(z))
            z_max = float(np.max(z))
        else:
            # Use percentiles for better color scaling with outliers
            z_valid = z[~nan_mask]
            if len(z_valid) > 0:
                z_min = np.percentile(z_valid, 5)
                z_max = np.percentile(z_valid, 95)

        # Get coordinate values
        if "lat" in var.dims and "lon" in var.dims:
            lats = var["lat"].values if "lat" in var.dims else np.arange(z.shape[-2])
            lons = var["lon"].values if "lon" in var.dims else np.arange(z.shape[-1])
        else:
            lats = np.arange(z.shape[-2]) if z.ndim >= 2 else [0]
            lons = np.arange(z.shape[-1]) if z.ndim >= 2 else [0]

        # Handle 2D data
        if z.ndim == 2:
            pass  # Good
        elif z.ndim == 3:
            # If there's an extra dimension, squeeze or take first
            if z.shape[0] == 1:
                z = z[0]
                lats = lats[:z.shape[0]] if len(lats) > z.shape[0] else lats
                lons = lons[:z.shape[1]] if len(lons) > z.shape[1] else lons
            else:
                z = z[0]
        else:
            # Lower dimensionality, squeeze
            z = np.squeeze(z)

        # Create contour plot
        fig = go.Figure(data=go.Contour(
            z=z,
            x=lons,
            y=lats,
            colorscale='RdYlBu_r',
            contours=dict(
                start=z_min,
                end=z_max,
                size=(z_max - z_min) / 10 if (z_max - z_min) > 0 else 1,
                coloring='fill'
            ),
            showscale=True,
            colorbar=dict(
                title=f"Value {var.attrs.get('units', '')}"
            ),
            hovertemplate='Lat: %{y}<br>Lon: %{x}<br>Value: %{z}<extra></extra>'
        ))

        # Update layout
        var_long_name = var.attrs.get("long_name", var_name)
        var_units = var.attrs.get("units", "")

        title = f"{var_long_name}"
        if var_units:
            title += f" ({var_units})"

        # Set axis labels based on coordinate values
        if len(lats) > 0 and len(lons) > 0:
            fig.update_layout(
                title=title,
                xaxis_title="Longitude",
                yaxis_title="Latitude",
                template="plotly_white",
                width=800,
                height=500,
                margin=dict(l=50, r=50, t=50, b=50),
                hovermode='closest'
            )
        else:
            fig.update_layout(
                title=title,
                template="plotly_white",
                width=800,
                height=500,
                margin=dict(l=50, r=50, t=50, b=50)
            )

        # Set axis ranges if we have coordinate values
        if len(lats) > 0 and len(lons) > 0:
            fig.update_xaxes(range=[float(lons.min()), float(lons.max())])
            fig.update_yaxes(range=[float(lats.min()), float(lats.max())],
                           autorange="reversed")  # Latitude reversed (North at top)

        return fig

    @staticmethod
    def plot_3d_surface(ds, var_name, time_idx=None):
        """
        Create a 3D surface plot of a variable.

        Parameters
        ----------
        ds : xr.Dataset
            The NetCDF dataset
        var_name : str
            Name of the variable to plot
        time_idx : int, optional
            Index into the time dimension

        Returns
        -------
        plotly.graph_objects.Figure
            3D surface figure
        """
        import numpy as np

        # Get the variable
        if var_name not in ds.data_vars:
            raise ValueError(f"Variable {var_name} not found in dataset")

        var = ds[var_name]

        # Apply time index selection
        if time_idx is not None:
            var = var.isel(time=time_idx)

        # Sanitize data
        var = NetCDFHandler.sanitize_data(var)

        # Get data values
        z = var.values.copy()
        nan_mask = np.isnan(z)

        if np.all(nan_mask):
            fig = go.Figure()
            fig.add_annotation(
                text="No valid data for 3D plot",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig

        # Replace NaN with minimum for surface
        z = np.where(nan_mask, np.nanmin(z[~nan_mask]) if np.any(~nan_mask) else 0, z)

        # Get coordinates
        if "lat" in var.dims and "lon" in var.dims:
            lats = var["lat"].values
            lons = var["lon"].values
        elif "x" in var.dims and "y" in var.dims:
            lons = var["x"].values
            lats = var["y"].values
        else:
            # Create coordinate arrays
            if z.ndim >= 2:
                lons = np.linspace(0, 1, z.shape[-1])
                lats = np.linspace(0, 1, z.shape[-2])
            else:
                lons = [0]
                lats = [0]

        # Create 3D surface
        fig = go.Figure(data=go.Surface(
            z=z,
            x=lons,
            y=lats,
            colorscale='RdYlBu_r',
            colorbar=dict(
                title=f"Value {var.attrs.get('units', '')}"
            ),
            hovertemplate='Lon: %{x}<br>Lat: %{y}<br>Value: %{z}<extra></extra>'
        ))

        var_long_name = var.attrs.get("long_name", var_name)
        var_units = var.attrs.get("units", "")

        title = f"{var_long_name}"
        if var_units:
            title += f" ({var_units})"

        fig.update_layout(
            title=title,
            scene=dict(
                xaxis_title="Longitude",
                yaxis_title="Latitude",
                zaxis_title="Value",
            ),
            template="plotly_white",
            width=800,
            height=600,
            margin=dict(l=50, r=50, t=50, b=50),
        )

        return fig

    @staticmethod
    def plot_animation(ds, var_name, frame_step=1):
        """
        Create an animated contour map showing variable evolution over time.

        Parameters
        ----------
        ds : xr.Dataset
            The NetCDF dataset
        var_name : str
            Name of the variable to plot
        frame_step : int
            Step size for frames (every Nth time step)

        Returns
        -------
        plotly.graph_objects.Figure
            Animated figure
        """
        import numpy as np

        # Get the variable
        if var_name not in ds.data_vars:
            raise ValueError(f"Variable {var_name} not found in dataset")

        var = ds[var_name]

        # Get time coordinates
        if "time" not in ds.coords:
            # No time dimension, create static plot without animation controls
            return PlotlyGenerator.plot_contour_map(ds, var_name)

        dt_idx = NetCDFHandler.parse_time(ds)
        frame_indices = list(range(0, len(dt_idx), frame_step))

        lat_name = "lat" if "lat" in var.dims else ("y" if "y" in var.dims else None)
        lon_name = "lon" if "lon" in var.dims else ("x" if "x" in var.dims else None)

        def _coords(arr):
            lats = arr[lat_name].values if lat_name else np.arange(arr.shape[-2])
            lons = arr[lon_name].values if lon_name else np.arange(arr.shape[-1])
            return lats, lons

        # Build frames
        frames = []
        labels = []
        for idx in frame_indices:
            try:
                frame_var = NetCDFHandler.sanitize_data(var.isel(time=idx))
                z = np.asarray(frame_var.values)
                if z.ndim != 2 or np.all(np.isnan(z)):
                    continue  # Skip non-spatial or all-NaN frames

                lats, lons = _coords(frame_var)
                label = str(dt_idx[idx])[:10]
                frames.append(go.Frame(
                    name=label,
                    data=[go.Contour(
                        z=z,
                        x=lons,
                        y=lats,
                        colorscale='RdYlBu_r',
                        showscale=True,
                        colorbar=dict(title=f"Value {var.attrs.get('units', '')}"),
                        hovertemplate='Lat: %{y}<br>Lon: %{x}<br>Value: %{z}<extra></extra>'
                    )]
                ))
                labels.append(label)
            except Exception:
                continue

        if not frames:
            fig = go.Figure()
            fig.add_annotation(text="No animatable data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig

        # Initial frame
        fig = go.Figure(data=frames[0].data, frames=frames)

        # Add slider
        steps = []
        for label in labels:
            steps.append(dict(
                label=label,
                method="animate",
                args=[[label], {"frame": {"duration": 200, "redraw": True},
                                "mode": "immediate",
                                "transition": {"duration": 0}}]
            ))

        sliders = [dict(
            active=0,
            currentvalue={"prefix": "Time: "},
            pad={"t": 60, "b": 10},
            steps=steps
        )]

        fig.update_layout(
            title=f"{var.attrs.get('long_name', var_name)} over Time",
            template="plotly_white",
            width=800,
            height=500,
            margin=dict(l=50, r=50, t=50, b=50),
            sliders=sliders,
            hovermode='closest',
            xaxis_title="Longitude",
            yaxis_title="Latitude",
        )

        return fig