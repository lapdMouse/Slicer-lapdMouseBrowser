# lapdMouseBrowser

**lapdMouseBrowser** is an extension for [3D Slicer](https://www.slicer.org) to
download and visualize files from the
[Lung anatomy + particle deposition (lapd) mouse archive](https://doi.org/10.25820/9arg-9w56).
For more information about the lapdMouse project and available data visit
<https://doi.org/10.25820/9arg-9w56>. More specifically, **lapdMouseBrowser** allows
the user to browse through the datasets in the lapdMouse data archive, download them
to the local drive, and load them in 3D Slicer. Advantages include:

  * GUI for users with no software development skills.
  * Visualize lapdMouse files not natively supported by 3D Slicer:
     * airway tree structure with branch labeling
     * aerosol deposition measurements
  * Download and visualize a set of commonly used files ("standard file
    selection") with a single click.
  * Pre-configured with suitable visualization parameters and color lookup
    tables for:
    * Volumetric images (aerosol and autofluorescent image data)
    * Labelmaps (lungs, lobes, near acini, airway segments)
    * Mesh models (airway segments, airway wall deposition)

## Installation

**lapdMouseBrowser** is an extension for [3D Slicer](https://www.slicer.org),
an open-source medical image processing and visualization system available for
all major operating systems.

**Prerequisite - 3D Slicer**: If 3D Slicer has not yet been installed on your system,
go to <https://download.slicer.org>, download and install a version suitable
for your operating system. We recommend the use of the latest stable release of
3D Slicer. **lapdMouseBrowser** has been developed for Slicer 5.6.1.

**Install lapdMouseBrowser**: Start 3D Slicer and select from the menu `View`
the `Extension Manager` and `Install Extensions`. Then search for
`lapdMouseBrowser`. Select it for installation and `restart` 3D Slicer.

## Usage

Start 3D Slicer with the installed **lapdMouseBrowser** extension.
For users not familiar with 3D Slicer, we refer to the
[3D Slicer user documentation](https://slicer.readthedocs.io/en/latest/index.html)
and its [Getting started](https://slicer.readthedocs.io/en/latest/user_guide/getting_started.html)
section.  From 3D Slicer's Module selector (drop down menu `Modules:` in
tool bar) select `lapdMouse`, `lapdMouseDBBrowser`. The **lapdMouse Data
Archive Browser** window opens.  On the left it lists all datasets
available in the data archive, on the right it shows a list of files and
actions associated with a selected dataset.

The following subsections will explain how to:

  * [Specify a local storage folder](#specifyalocalstoragefolder)
  * [Download and visualize a standard set of files](#downloadandvisualizeastandardsetoffiles)
  * [Download and visualize a custom set of files](#downloadandvisualizeacustomsetoffiles)
  * [Visualization of files not natively supported by 3D Slicer](#visualizationoffilesnotnativelysupportedby3dslicer)

### Specify a local storage folder

**lapdMouseBrowser** stores downloaded files in folder `./lapdMouse` by default.
If you want to change the default storage directory, close the lapdMouse Data Archive
Browser window, change the `Storage Folder` using the lapdMouseBrowser's 3D
Slicer module panel (panel on left side of 3D Slicer main window) and reopen the
lapdMouse Data Archive Browse window by clicking "Show browser".

### Download and visualize a standard set of files

In the **lapdMouse Data Archive Browser** window select on the left side the dataset
you want to load. Then on the right side click `load standard file selection
in Slicer`.

The "standard" file selection includes files commonly used:

  * `AerosolSub4.mha` (aerosol deposition image volume)
  * `AutofluorescentSub4.mha` (autofluorescent image volume showing anatomical
    structures)
  * `Lobes.nrrd` (Labelmap for lung lobes)
  * `AirwayOutlets.vtk` (Airway mesh with label assigned to outlets)
  * `AirwayWallDeposition.vtk` (aerosol deposition measurements near the airway
    wall)

![lapdMouseBrowser main
window](https://raw.githubusercontent.com/lapdMouse/Slicer-lapdMouseBrowser/master/Screenshots/LapdMouseDBBrowserWindow.png)

If the files have not yet been downloaded, **lapdMouseBrowser** will display the
total size of the files and ask the user to confirm the download. **Note:** Some
files in the data archive such as full resolution volumetric images are several GB
in size. Depending on your internet speed, the download might take several
minutes. Files that are available on the local hard drive have a different
status icon and will not have to be downloaded again.

Once the files are locally available, they will be loaded into 3D Slicer with
suitable color lookup tables and default visualization parameters (e.g.
gray-value window). After loading the standard files, 3D Slicer displays the
aerosol deposition image and the airway wall deposition measurements mesh, and
an outline of the lung lobes. The visualization parameters and displayed models
can then be modified using 3D Slicer's standard functionality.

![Loaded standard file selection](https://raw.githubusercontent.com/lapdMouse/Slicer-lapdMouseBrowser/master/Screenshots/LapdMouseStandardFiles.png)

### Download and visualize a custom set of files

If you want to download additional (or other) files for a dataset, select the
file names from the list (ust `Ctrl`-key to select multiple at once), and click
`download selected files`. **lapdMouseBrowser** will display the total size of
the files and ask the user to confirm the download. After download, they get can
get loaded in 3D Slicer using `load selected files`.

![Visualized airway tree structure and near acini compartment deposition](https://raw.githubusercontent.com/lapdMouse/Slicer-lapdMouseBrowser/master/Screenshots/LapdMouseNearAciniTree.png)

### Visualization of files not natively supported by 3D Slicer

**lapdMouseBrowser** includes **lapdMouseVisualizer**, a 3D Slicer module to
create mesh models for visualization of lapdMouse files not natively support by
3D Slicer:
  * airway tree structure with branch labeling stored as `*.meta` files
  * aerosol deposition measurement tables stored as `*.csv` files

To create visualizations of these files, select from the  3D Slicer's Module
selector, `lapdMouse`, `lapdMouseVisualizer`. Then, under Section `Tree Structure`
or `Compartment Measurements`, select the the input file, an output model, and
click `Apply`.

The airway tree structure are rendered as a set of cylinder elements with a
color coding of labeled branches. Compartment aerosol deposition measurements
are rendered as spheres with a color coding of the measurement value.

## Note on 3D Slicer's coordinate systems
One of the issues while dealing with volumetric images and derived models are
the differences between the coordinate systems. See
https://slicer.readthedocs.io/en/latest/user_guide/coordinate_systems.html
for an explanation.

All lapdMouse data (images, meshes, tree structure, etc.) were generated with
[Insight Segmentation and Registration Toolkit](https://itk.org) (ITK) and use
an **LPS** coordinate system.

3D Slicer however, loads raster images assuming an LPS coordinate system and
models assuming an RAS coordinate system; see [Slicer File Formats](https://slicer.readthedocs.io/en/latest/user_guide/data_loading_and_saving.html).
As a result, when loading images and meshes 3D Slicer's `Add data`, they seem
to not match.
To fix this manually, one needs to transform either the images or the models.
After loading the datasets, go to Slicer's `Transforms` module, and select 
from `Active Transform` `Create new Linear Transform`. Specify the
`Transformation Matrix` to flip the data in the first two dimensions:

    -1  0  0  0
     0 -1  0  0
     0  0  1  0
     0  0  0  1

Then, in Section `Apply transform` move the models from `Transformable` to
`Transformed`. Then loaded images and models are aligned.

**lapdMouseDBBrowser** takes care of these steps automatically when loading
models.

## License

**lapdMouseBrowser** is distributed under [3-clause BSD license](License.txt).

## Acknowledgements

This work was supported in part by NIH project R01ES023863.

## Support

For support and further information please visit the
"Lung anatomy + particle deposition (lapd) mouse archive"
at <https://doi.org/10.25820/9arg-9w56> or our data repository at
[NIEHS](https://cebs-ext.niehs.nih.gov/cahs/report/lapd/web-download-links/MzNhZGRkZGY5ZWU2OGU1ODgwYWQ4NjA2Njg0M2Q1YzMK)

