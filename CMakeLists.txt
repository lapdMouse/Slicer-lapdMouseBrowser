cmake_minimum_required(VERSION 3.5)

project(lapdMouseBrowser)

#-----------------------------------------------------------------------------
# Extension meta-information

set(EXTENSION_Name "lapdMouseBrowser")
set(EXTENSION_HOMEPAGE "http://slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/lapdMouseBrowser")
set(EXTENSION_CATEGORY "Informatics")
set(EXTENSION_CONTRIBUTORS "Christian Bauer (Univeristy of Iowa), Melissa Krueger (University of Washington")
set(EXTENSION_DESCRIPTION "Connect to the lapdMouse archive, browse the collection, download and visualize data files in 3D Slicer.")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/lapdMouse/Slicer-lapdMouseBrowser/master/lapdMouseBrowser.png")
set(EXTENSION_SCREENSHOTURLS "https://raw.githubusercontent.com/lapdMouse/Slicer-lapdMouseBrowser/master/Screenshots/LapdMouseDBBrowserWindow.png https://raw.githubusercontent.com/lapdMouse/Slicer-lapdMouseBrowser/master/Screenshots/LapdMouseStandardFiles.png https://raw.githubusercontent.com/lapdMouse/Slicer-lapdMouseBrowser/master/Screenshots/LapdMouseNearAciniTree.png")
set(EXTENSION_DEPENDS "NA") # Specified as a space separated string, a list or 'NA' if any

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(lapdMouseDBBrowser)
add_subdirectory(lapdMouseVisualizer)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
