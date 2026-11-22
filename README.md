# 🌊 NetCDF Variable Plotter

**Interactive web application for plotting any variable from NetCDF files.**

![NetCDF Plotter Banner](https://img.shields.io/badge/Streamlit-ff4b4b?style=for-the-badge&logo=streamlit)
![Python](https://img.shields.io/badge/Python-3.10+-yellow?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)

---

## 📋 Table of Contents

1. [Installation](#-installation)
2. [Quick Start](#-quick-start)
3. [Using the Application](#-using-the-application)
   - [Variable Selection](#-variable-selection)
   - [Plot Types](#-plot-types)
   - [Spatial & Temporal Subsetting](#-spatial--temporal-subsetting)
   - [Download Options](#-download-options)
4. [Supported Variables](#-supported-variables)
5. [Error Handling](#-error-handling)
6. [Troubleshooting](#-troubleshooting)
7. [License](#-license)

---

## 🔧 Installation

### Prerequisites
- Python 3.10 or higher
- pip package manager

### Install via pip
```bash
# Clone or download this repository
git clone https://github.com/the-partha/NC_Plotter_Web_App.git
cd nc-plotter-app

# Create and activate virtual environment (recommended)
python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Requirements
The following packages are installed via `requirements.txt`:
- `numpy` - Array operations
- `xarray` - NetCDF I/O and coordinate labeling
- `plotly` - Interactive plots
- `matplotlib` - Static publication-quality plots
- `cftime` - Advanced time handling
- `scipy` - Statistical functions (KDE distributions)
- `pandas` - Time series handling
- `streamlit` - Web application framework

---

## 🚀 Quick Start

### 1. Launch the Application
```bash
streamlit run nc_plotter_app/app.py
```

### 2. Access in Browser
Open `http://localhost:8501` in your web browser.

### 3. Upload a NetCDF File
- Click the **"Choose a NetCDF file (.nc)"** button in the sidebar
- Select any `.nc` file from your system
- Wait for the dataset to load successfully

### 4. Select a Variable
- The app will automatically list **all variables** in your dataset
- Browse the expander section to view variable details:
  - Variable name
  - Long name description
  - Units of measurement
  - Dimensions and shape
- Check the checkbox next to the variable you want to plot

### 5. Choose Plot Type
- **Plotly Interactive**: Zooming, panning, tooltips, animation
- **Matplotlib Static**: Publication-quality static plots

### 6. Adjust & View
- Use time range sliders if applicable
- Use latitude/longitude sliders for spatial subsetting
- View your plot in the main window

### 7. Download
- Download plots as PNG images (Matplotlib)
- Download plot data as JSON (Plotly)
- Export variable metadata as needed

---

## 🎨 Using the Application

### 🔍 Variable Selection
The key feature of this app is **explicit variable selection**. Unlike other tools that assume specific variable names (like `rainfall` or `t2m`), this app:

1. **Scans your `.nc` file** and lists **ALL variables** automatically
2. **Displays detailed information** for each variable:
   - Variable name
   - Long name description (from CF conventions)
   - Units of measurement
   - Dimensions and array shape
3. **Lets you select exactly which variable** to plot, regardless of its name

### 📈 Plot Types

#### Plotly Interactive Plots
- **Time Series**: Interactive line plot with zooming, panning, and tooltips
- **Contour Map**: Interactive spatial contour plot with hover data
- **3D Surface**: 3D surface plot showing variable evolution over time
- **Animation**: Animated contour map showing variable evolution over all time steps

#### Matplotlib Static Plots
- **Contour Map**: Filled contour plot with colorbar (publication-quality)
- **Time Series**: Publication-quality line plot with date formatting
- **Rainfall Distribution**: Histogram with Kernel Density Estimate (KDE)

### 🗺️ Spatial & Temporal Subsetting

#### Spatial Subsetting (Lat/Lon)
- Check the **"Spatial subsetting"** box
- Use sliders to select latitude range (e.g., `-30°` to `30°`)
- Use sliders to select longitude range (e.g., `0°` to `360°`)
- Subsetting applies to all selected variables simultaneously

#### Temporal Subsetting (Time Range)
- Use the **"Time range"** slider to select a subset of time steps
- Select specific time steps for contour maps and 3D surfaces
- Filter time series to specific date ranges

### 📥 Download Options

#### Plotly Plots
- **"Download plot data as JSON"** - Downloads plot data in JSON format
- Per-variable JSON files available for multi-variable datasets

#### Matplotlib Plots
- **"Download plot as PNG"** - High-resolution PNG image (150 DPI)
- Available for: Contour Map, Time Series, Rainfall Distribution
- Automatic cleanup of temporary files

#### Data Export
- Export variable metadata and attributes
- ZIP export containing information for all selected variables

---

## 📦 Supported Variables

The app works with **ANY variable name** in your NetCDF file. Examples include:

| Variable Name | Typical Description | Units |
|--------------|-------------------|-------|
| `rainfall`, `precip`, `pr`, `rr` | Rainfall/Precipitation | mm/day, kg/m²/s |
| `t2m`, `tas`, `temp`, `air_temp` | 2-meter Temperature | K, °C |
| `u10`, `v10`, `wind`, `wspd` | Wind Components/Speed | m/s |
| `sst`, `sea_surface_temp` | Sea Surface Temperature | K |
| `pres`, `pressure`, `msl` | Pressure/Pressure Level | hPa, Pa |
| `humid`, `hum`, `moisture` | Specific Humidity | kg/kg, g/kg |
| `fake_data`, `custom_var` | Custom/user-defined variables | Varies |

**The app automatically:**
- Detects the variable's dimensions and shape
- Handles fill values (`-999`, `9.96921e+36`, etc.)
- Parses time units (`hours since 2000-01-01`, `days since 1970-01-01`)
- Validates lat/lon coordinate ranges
- Sanitizes data for plotting (replaces fill values with NaN)

---

## ⚠️ Error Handling

The application robustly handles common NetCDF errors:

| Error Type | How It's Handled |
|------------|-----------------|
| **Fill values** (`-999`, `9.96921e+36`) | Automatically replaced with `NaN` |
| **Dimension ordering** | Auto-detects and corrects to `(time, lat, lon)` |
| **Time units** | Parses `since_epoch`, `since_2000`, `days since`, `hours since` |
| **Coordinate ranges** | Warns if lat > 90° or lon > 180° |
| **Missing data** | Uses `NaN` propagation, avoids plot errors |
| **Missing attributes** | Provides fallback labels and units |

---

## 🛠️ Troubleshooting

### Common Issues

| Issue | Solution |
|--------|----------|
| **File won't upload** | Ensure file is a valid `.nc` format. Check file size (very large files may timeout). |
| **No variables listed** | Verify the file is CF-compliant NetCDF. Some non-standard files may not list variables. |
| **Variable selection doesn't work** | Make sure you've checked the checkbox next to the variable name in the expander. |
| **Plot appears empty** | Check that the variable has valid data (not all fill values). Try adjusting spatial/temporal subsetting. |
| **Time axis looks wrong** | Ensure your NetCDF file has CF-compliant time attributes (`units`, `calendar`). |
| **Memory error with large files** | The app uses chunked loading by default. Consider selecting a smaller time/space subset. |
| **Plot colorbar scale seems off** | Use spatial subsetting to focus on your region of interest, which improves color scaling. |

### Need More Help?
- Check the [Issues](https://github.com/the-partha/NC_Plotter_Web_App/issues) page
- Ensure your NetCDF file follows CF conventions (units, long_name, standard_name attributes)
- Contact support via the repository

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2026 NetCDF Variable Plotter

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🎓 Quick Reference Cheat Sheet

| Action | Shortcut |
|--------|----------|
| Upload file | Click sidebar button |
| Select variable | Check checkbox in expander |
| Toggle plot type | Radio button in sidebar |
| Spatial subsetting | Check "Spatial subsetting" box + use sliders |
| Temporal subsetting | Use "Time range" slider |
| Download PNG | Click "Download plot as PNG" button |
| Download JSON | Click "Download plot data as JSON" button |
| Reset/start over | Refresh the browser page |

---

## 📞 Support & Feedback

- **Report bugs**: Open an issue on the [GitHub repository](https://github.com/the-partha/NC_Plotter_Web_App)
- **Feature requests**: Submit a feature request on GitHub
- **Questions**: Start a discussion on the [Discussions](https://github.com/the-partha/NC_Plotter_Web_App/discussions) page
- **Email**: contact@thepartha.in

---

*Built with Streamlit, Xarray, Plotly & Matplotlib | Last updated: November 2026*
