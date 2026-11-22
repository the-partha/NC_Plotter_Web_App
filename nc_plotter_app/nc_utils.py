"""
nc_utils.py - Robust NetCDF handling utilities for spatio-temporal datasets.

Handles common errors in rainfall, t2m, and similar CF-convention NetCDF files:
- Fill value replacement
- Dimension reordering
- Time unit parsing
- Coordinate variable validation
- Unit awareness
- Memory-efficient chunked loading
"""

import numpy as np
import xarray as xr
import cftime


class NetCDFHandler:
    """Robust NetCDF file handler with error detection and sanitization."""

    # Common fill values that need replacement with NaN
    COMMON_FILL_VALUES = [
        -999,
        -99.99,
        9.96921e+36,
        9.96921e+35,
        -9.96921e+36,
        -9999,
        -999.0,
    ]

    @staticmethod
    def load_dataset(uploaded_file, chunks=None):
        """
        Load a NetCDF dataset with memory-efficient chunking and error handling.

        Parameters
        ----------
        uploaded_file : file-like object
            Path to .nc file or uploaded file object
        chunks : dict, optional
            Chunk sizes for lazy loading. Defaults to memory-safe sizes.

        Returns
        -------
        xr.Dataset
            Loaded and standardized dataset
        """
        # Chunked loading requires dask. Fall back to eager loading when it is
        # not installed so the app still works in a minimal environment.
        try:
            import dask  # noqa: F401
            use_chunks = chunks if chunks is not None else {"time": 1, "lat": 100, "lon": 100}
        except ImportError:
            use_chunks = None

        def _open(decode_cf):
            if use_chunks is not None:
                return xr.open_dataset(uploaded_file, chunks=use_chunks, decode_cf=decode_cf)
            return xr.open_dataset(uploaded_file, decode_cf=decode_cf)

        try:
            ds = _open(True)
        except Exception as e:
            # Try without CF decoding if CF decoding fails
            try:
                if hasattr(uploaded_file, "seek"):
                    uploaded_file.seek(0)
                ds = _open(False)
                print("Warning: Loaded without CF decoding - some attributes may be missing")
            except Exception as e2:
                raise ValueError(f"Failed to open NetCDF file: {e2}")

        # Standardize dimension order and coordinate labeling
        ds = NetCDFHandler.standardize_dataset(ds)

        return ds

    @staticmethod
    def standardize_dataset(ds):
        """
        Standardize dataset: fix dimension order, coordinate variables, and attrs.

        Ensures consistent (time, lat, lon) ordering and valid geographic coordinates.
        """
        # 1. Fix dimension order to (time, lat, lon) if possible
        ds = NetCDFHandler._reorder_dimensions(ds)

        # 2. Validate and fix coordinate variables
        ds = NetCDFHandler._validate_coordinates(ds)

        # 3. Ensure all data variables have units attribute
        for var_name in ds.data_vars:
            if "units" not in ds[var_name].attrs:
                # Try to infer from standard_name or long_name
                ds[var_name].attrs.setdefault("units", "")

        return ds

    @staticmethod
    def _reorder_dimensions(ds):
        """
        Reorder dimensions to standard (time, lat, lon) order.

        Handles common variations:
        - (time, lat, lon) -> already standard
        - (time, lon, lat) -> swap last two
        - (lat, lon, time) -> move time to front
        """
        dims = list(ds.sizes.keys())
        if "time" in dims and "lat" in dims and "lon" in dims:
            current_order = dims
            if current_order != ["time", "lat", "lon"]:
                # Find indices of time, lat, lon
                time_idx = current_order.index("time") if "time" in current_order else -1
                lat_idx = current_order.index("lat") if "lat" in current_order else -1
                lon_idx = current_order.index("lon") if "lon" in current_order else -1

                if time_idx >= 0 and lat_idx >= 0 and lon_idx >= 0:
                    # Build new order: time first, then lat, then lon
                    new_order = ["time", "lat", "lon"]
                    # Get remaining dimensions in their original relative order
                    remaining = [d for d in current_order if d not in new_order]
                    new_order.extend(remaining)
                    ds = ds.transpose(*new_order)
                    print(f"Reordered dimensions from {current_order} to {new_order}")

        return ds

    @staticmethod
    def _validate_coordinates(ds):
        """
        Validate coordinate variables and warn on geographic inconsistencies.
        """
        # Check lat/lon ranges
        if "lat" in ds.coords:
            lat_values = ds["lat"].values
            if np.any(lat_values > 90) or np.any(lat_values < -90):
                print(
                    f"Warning: Latitude values outside [-90, 90]. "
                    f"Range: [{lat_values.min()}, {lat_values.max()}]"
                )

        if "lon" in ds.coords:
            lon_values = ds["lon"].values
            # Normalize to [-180, 180] if outside range
            if np.any((lon_values > 180) & (lon_values < 360)):
                print(
                    f"Warning: Longitude values in [0, 360] detected. "
                    f"Consider normalizing to [-180, 180]. Range: "
                    f"[{lon_values.min()}, {lon_values.max()}]"
                )

        # Ensure lat is sorted ascending for consistency
        if "lat" in ds.coords:
            if not np.all(np.diff(ds["lat"].values) > 0):
                ds = ds.sortby("lat")
                print("Sorted latitude coordinate ascending")

        return ds

    @staticmethod
    def sanitize_data(var):
        """
        Sanitize a DataArray for plotting by handling fill values and missing data.

        Parameters
        ----------
        var : xr.DataArray
            Variable to sanitize

        Returns
        -------
        xr.DataArray
            Sanitized variable with NaN replacing fill values
        """
        # 1. Replace _FillValue or missing_value attr with NaN
        fill_attrs = var.attrs.get("_FillValue", var.attrs.get("missing_value", None))
        if fill_attrs is not None:
            # Convert to numpy for comparison
            if np.isscalar(fill_attrs):
                fill_val = float(fill_attrs)
                var = var.where(var != fill_attrs, np.nan)
                print(f"Replaced _FillValue {fill_val} with NaN")

        # 2. Replace common fill values if not already done
        var_array = var.values
        for cv in NetCDFHandler.COMMON_FILL_VALUES:
            mask = np.isclose(var_array, cv, rtol=1e-3)
            if np.any(mask):
                var = var.where(~mask, np.nan)
                print(f"Replaced common fill value {cv} with NaN")
                break  # Only replace first common type found

        # 3. Ensure float type and NaN propagation
        var = var.astype(float)
        var = var.fillna(np.nan)

        # 4. Clip extreme values (warn but don't clip by default)
        # Rainfall values < 0 or > 1000 mm/day are suspect
        if var.name and "rain" in str(var.name).lower():
            if float(var.min()) < 0:
                print(f"Warning: Variable {var.name} has negative values")
            if float(var.max()) > 1000:
                print(f"Warning: Variable {var.name} values > 1000 (may need unit conversion)")

        return var

    @staticmethod
    def parse_time(ds):
        """
        Parse time coordinate from CF-convention NetCDF dataset.

        Handles various time unit formats:
        - 'hours since 2000-01-01 00:00:00'
        - 'days since 1970-01-01'
        - 'since_epoch' (unix timestamps)

        Returns
        -------
        pd.DatetimeIndex
            Parsed time axis
        """
        if "time" not in ds.coords:
            raise ValueError("No time coordinate found in dataset")

        import pandas as pd

        time_vals = ds["time"].values

        # xarray normally decodes time to datetime64 already; in that case the
        # original "units" attribute is gone, so use the values directly.
        if np.issubdtype(np.asarray(time_vals).dtype, np.datetime64):
            return pd.DatetimeIndex(np.asarray(time_vals))

        if np.issubdtype(np.asarray(time_vals).dtype, np.timedelta64):
            return pd.DatetimeIndex(pd.Timestamp("1970-01-01") + time_vals)

        time_units = ds["time"].attrs.get("units", "")
        time_calendar = ds["time"].attrs.get("calendar", "standard")

        if not time_units:
            # Last resort: treat the values as a numeric index.
            return pd.Index(time_vals)

        try:
            # Use cftime.num2date for advanced time handling
            dates = cftime.num2date(time_vals, time_units, calendar=time_calendar)

            # Convert to pandas DatetimeIndex
            if hasattr(dates, "__iter__") and not isinstance(dates, str):
                dt_idx = pd.DatetimeIndex(dates)
                return dt_idx
            else:
                dt_idx = pd.DatetimeIndex([dates])
                return dt_idx

        except Exception as e:
            # Fallback: try manual parsing
            print(f"cftime parsing failed: {e}, trying fallback")
            try:
                # Try direct pandas conversion
                dt_idx = pd.to_datetime(time_vals, unit=None)
                return dt_idx
            except Exception as e2:
                raise ValueError(f"Failed to parse time: {e2}")

    @staticmethod
    def get_variable_info(ds):
        """
        Extract variable information for UI display.

        Returns list of dicts with variable name, units, long_name, dims, etc.
        """
        info = []
        for var_name in ds.data_vars:
            var = ds[var_name]
            info.append(
                {
                    "name": var_name,
                    "dims": list(var.dims),
                    "shape": var.shape,
                    "units": var.attrs.get("units", ""),
                    "long_name": var.attrs.get("long_name", var_name),
                    "standard_name": var.attrs.get("standard_name", ""),
                    "_FillValue": var.attrs.get("_FillValue", None),
                    "missing_value": var.attrs.get("missing_value", None),
                }
            )
        return info

    @staticmethod
    def get_time_range(ds):
        """Get the time range of the dataset as (start, end) strings."""
        if "time" not in ds.coords:
            return None

        dt_idx = NetCDFHandler.parse_time(ds)
        if dt_idx is not None and len(dt_idx) > 0:
            return (str(dt_idx[0]), str(dt_idx[-1]))
        return None

    @staticmethod
    def get_spatial_bounds(ds):
        """Get spatial bounds (lat/lon min/max) from dataset."""
        bounds = {"lat": None, "lon": None}

        if "lat" in ds.coords:
            bounds["lat"] = (float(ds["lat"].min()), float(ds["lat"].max()))

        if "lon" in ds.coords:
            bounds["lon"] = (float(ds["lon"].min()), float(ds["lon"].max()))

        return bounds