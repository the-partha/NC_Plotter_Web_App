"""
matplotlib_generator.py - Static Matplotlib plots for spatio-temporal NetCDF data.

Provides high-quality static publication-grade plots using Matplotlib for exploring
gridded rainfall, temperature, and similar CF-convention NetCDF datasets. Handles
fill values, units labeling, and various plot types including contour maps, time series,
and histograms.
"""

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

try:
    from .nc_utils import NetCDFHandler
except ImportError:  # Allow importing this module directly
    from nc_utils import NetCDFHandler


class MatplotlibGenerator:
    """Generate static Matplotlib plots for NetCDF data."""

    @staticmethod
    def plot_contourf_map(ds, var_name, time_idx=None, cbar_label=None):
        """
        Create a filled contour map for a variable at a given time index.

        Parameters
        ----------
        ds : xr.Dataset
            The NetCDF dataset
        var_name : str
            Name of the variable to plot
        time_idx : int, optional
            Index into the time dimension. If None, uses the middle time step.
        cbar_label : str, optional
            Colorbar label. If None, uses variable units + long_name.

        Returns
        -------
        matplotlib.figure.Figure
            Contour figure
        """
        import matplotlib as mpl

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

        # Check if we have valid data
        if np.all(np.isnan(z)):
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.text(0.5, 0.5, "No valid data available for this selection",
                    ha='center', va='center', transform=ax.transAxes)
            return fig, ax

        # Get coordinate values
        if "lat" in var.dims and "lon" in var.dims:
            lats = var["lat"].values
            lons = var["lon"].values
        elif "x" in var.dims and "y" in var.dims:
            lons = var["x"].values
            lats = var["y"].values
        else:
            # Create default coordinates
            lons = np.arange(z.shape[-1]) if z.ndim >= 2 else np.arange(10)
            lats = np.arange(z.shape[-2]) if z.ndim >= 2 else [0]

        # Handle 2D/3D data
        if z.ndim == 3:
            # Take first time step if 3D
            z = z[0]
            if lats.ndim == 1 and len(lats) > z.shape[0]:
                lats = lats[:z.shape[0]]
            if lons.ndim == 1 and len(lons) > z.shape[1]:
                lons = lons[:z.shape[1]]
        elif z.ndim == 1:
            z = z.reshape(1, -1)
            lats = [lats] if len(lats) == 1 else lats
            lons = [lons] if len(lons) == 1 else lons

        # Set up colormap and normalization
        var_units = var.attrs.get("units", "")
        long_name = var.attrs.get("long_name", var_name)

        # Remove NaN for colormap scaling, but keep mask for plotting
        z_valid = z[~np.isnan(z)] if np.any(~np.isnan(z)) else [0]
        if len(z_valid) > 0:
            vmin = float(np.percentile(z_valid, 5))
            vmax = float(np.percentile(z_valid, 95))
        else:
            vmin, vmax = 0, 1

        # Create filled contour plot
        if cbar_label is None:
            cbar_label = f"{long_name} {var_units}".strip() if var_units else long_name

        fig, ax = plt.subplots(figsize=(8, 6))
        cf = ax.contourf(lons, lats, z, levels=15, cmap='RdYlBu_r',
                         vmin=vmin, vmax=vmax,
                         extend='both')

        # Add a subtle grid for geographic data
        ax.grid(True, alpha=0.3, linestyle="--")

        # Set labels
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        # Reverse latitude axis (North at top)
        ax.set_ylim(max(lats), min(lats))

        # Add colorbar
        cbar = fig.colorbar(cf, ax=ax, shrink=0.8, pad=0.05)
        cbar.set_label(cbar_label, fontsize=10)

        # Title
        title = long_name
        if var_units:
            title += f" ({var_units})"

        fig.suptitle(title, fontsize=12)

        return fig, ax

    @staticmethod
    def plot_timeseries(ds, var_name, time_range=None):
        """
        Create a publication-quality time series plot.

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
        matplotlib.figure.Figure
            Time series figure
        """
        import matplotlib.dates as mdates
        import pandas as pd

        # Get the variable
        if var_name not in ds.data_vars:
            raise ValueError(f"Variable {var_name} not found in dataset")

        var = ds[var_name]

        # Apply time range filter if specified
        if time_range and "time" in ds.coords:
            start, end = time_range
            if isinstance(start, (int, np.integer)) and isinstance(end, (int, np.integer)):
                var = var.isel(time=slice(int(start), int(end) + 1))
            else:
                dt_idx = NetCDFHandler.parse_time(ds)
                if dt_idx is not None:
                    try:
                        start_dt = pd.to_datetime(start)
                        end_dt = pd.to_datetime(end)
                        mask = (dt_idx >= start_dt) & (dt_idx <= end_dt)
                        var = var.sel(time=mask)
                    except Exception:
                        pass

        # Sanitize data
        var = NetCDFHandler.sanitize_data(var)

        # Compute timeseries (mean over space if spatial dims exist)
        if "time" in var.coords:
            try:
                times = pd.DatetimeIndex(var["time"].values)
            except Exception:
                times = NetCDFHandler.parse_time(ds)
        else:
            times = NetCDFHandler.parse_time(ds)

        if "lat" in var.dims and "lon" in var.dims:
            ts = var.mean(dim=["lat", "lon"]).values
        elif "lat" in var.dims:
            ts = var.mean(dim="lat").values
        elif "lon" in var.dims:
            ts = var.mean(dim="lon").values
        else:
            ts = var.values

        # Convert to pandas for easy handling
        ts_pd = pd.Series(ts, index=pd.DatetimeIndex(times))

        # Drop NaN
        ts_pd = ts_pd.dropna()

        if len(ts_pd) == 0:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, "No data available for the selected time range",
                    ha='center', va='center', transform=ax.transAxes)
            return fig, ax

        # Create time series plot
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(ts_pd.index, ts_pd.values, 'b-', linewidth=1.5, label=var.attrs.get('long_name', var_name))

        # Format x-axis as dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        fig.autofmt_xdate()

        # Fill area between line and 0 for rainfall-like data
        if "rain" in var.attrs.get("units", "").lower() or "precip" in var_name.lower():
            ax.fill_between(ts_pd.index, ts_pd.values, 0, color='lightblue', alpha=0.3)

        # Title and labels
        var_units = var.attrs.get("units", "")
        long_name = var.attrs.get("long_name", var_name)

        ax.set_title(f"{long_name}" + (f" ({var_units})" if var_units else ""),
                     fontsize=14)
        ax.set_ylabel(f"Value {var_units}" if var_units else "Value", fontsize=12)
        ax.set_xlabel("Date", fontsize=12)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)

        # Set y-axis auto-range with some padding
        if len(ts_pd) > 0:
            y_range = ts_pd.max() - ts_pd.min()
            padding = y_range * 0.1 if y_range > 0 else 1
            ax.set_ylim(ts_pd.min() - padding, ts_pd.max() + padding)

        return fig, ax

    @staticmethod
    def plot_rainfall_distribution(ds, var_name):
        """
        Create a histogram of rainfall values with KDE.

        Parameters
        ----------
        ds : xr.Dataset
            The NetCDF dataset
        var_name : str
            Name of the rainfall variable

        Returns
        -------
        matplotlib.figure.Figure
            Histogram figure
        """
        import scipy.stats as stats

        # Get the variable
        if var_name not in ds.data_vars:
            raise ValueError(f"Variable {var_name} not found in dataset")

        var = ds[var_name]

        # Sanitize data
        var = NetCDFHandler.sanitize_data(var)

        # Get values, dropping NaN
        values = np.asarray(var.values).ravel()
        values = values[np.isfinite(values)]

        if len(values) == 0:
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.text(0.5, 0.5, "No valid data for distribution plot",
                    ha='center', va='center', transform=ax.transAxes)
            return fig, ax

        # Create histogram with KDE
        fig, ax = plt.subplots(figsize=(8, 6))

        # Plot histogram
        n, bins, patches = ax.hist(values, bins='auto', density=True,
                                   alpha=0.7, color='skyblue',
                                   edgecolor='white', linewidth=1.2)

        # Plot KDE
        kde = stats.gaussian_kde(values)
        x_range = np.linspace(values.min(), values.max(), 200)
        ax.plot(x_range, kde(x_range), 'r-', linewidth=2, label='KDE')

        # Add statistics line
        mean_val = np.mean(values)
        median_val = np.median(values)
        ax.axvline(mean_val, color='orange', linestyle='--', linewidth=1.5,
                   label=f'Mean: {mean_val:.2f}')
        ax.axvline(median_val, color='green', linestyle='--', linewidth=1.5,
                   label=f'Median: {median_val:.2f}')

        # Labels and title
        var_units = var.attrs.get("units", "")
        long_name = var.attrs.get("long_name", var_name)

        ax.set_title(f"Distribution: {long_name}" + (f" ({var_units})" if var_units else ""),
                     fontsize=14)
        ax.set_xlabel(f"Value {var_units}" if var_units else "Value", fontsize=12)
        ax.set_ylabel("Density", fontsize=12)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)

        # Set x-axis limits with some padding
        val_range = values.max() - values.min()
        padding = val_range * 0.1 if val_range > 0 else 1
        ax.set_xlim(values.min() - padding, values.max() + padding)

        return fig, ax

    @staticmethod
    def plot_monthly_mean(ds, var_name):
        """
        Create a plot of monthly mean values.

        Parameters
        ----------
        ds : xr.Dataset
            The NetCDF dataset
        var_name : str
            Name of the variable

        Returns
        -------
        matplotlib.figure.Figure
            Monthly mean figure
        """
        import pandas as pd

        # Get the variable
        if var_name not in ds.data_vars:
            raise ValueError(f"Variable {var_name} not found in dataset")

        var = ds[var_name]

        # Sanitize data
        var = NetCDFHandler.sanitize_data(var)

        # Check for time dimension
        if "time" not in var.dims:
            # No time dimension, just plot the variable
            fig, ax = MatplotlibGenerator.plot_contourf_map(ds, var_name)
            return fig, ax

        # Compute monthly means
        try:
            monthly_mean = var.groupby("time.month").mean(dim="time")
        except Exception:
            # Fallback: manual monthly grouping
            monthly_mean = None

        if monthly_mean is None or monthly_mean.size == 0:
            # Can't compute monthly means, plot original
            fig, ax = MatplotlibGenerator.plot_contourf_map(ds, var_name)
            return fig, ax

        # Plot each month
        fig, ax = plt.subplots(figsize=(10, 8))

        months = range(1, 13)
        colors = plt.cm.Set3(np.linspace(0, 1, 12))

        for month, color in zip(months, colors):
            try:
                month_data = monthly_mean.sel(month=month)
                if month_data is not None and not np.all(np.isnan(month_data.values)):
                    # Plot this month's mean
                    cf = ax.contourf(month_data["lon"], month_data["lat"],
                                     month_data.values, levels=10,
                                     cmap='RdYlBu_r', alpha=0.8,
                                     colors=[color] if month == 1 else [color])
                    # Add contour lines
                    ax.contour(month_data["lon"], month_data["lat"],
                               month_data.values, levels=5,
                               colors='k', alpha=0.5, linewidths=0.5)
            except Exception:
                continue

        # Formatting
        ax.set_title("Monthly Mean Values", fontsize=14)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_ylim(max(monthly_mean["lat"].values), min(monthly_mean["lat"].values))
        ax.grid(True, alpha=0.3, linestyle="--")

        # Create legend/colorbar
        cf = ax.contourf(monthly_mean.isel(month=1)["lon"], monthly_mean.isel(month=1)["lat"],
                         monthly_mean.isel(month=1).values, levels=10,
                         cmap='RdYlBu_r')
        cbar = fig.colorbar(cf, ax=ax, shrink=0.8, pad=0.05)
        cbar.set_label("Value")

        # Add month labels
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        ax.set_xticks([])  # Clean up
        ax.set_yticks([])

        return fig, ax