# Package or deploy the QGIS 3/4 Profile Tool plugin.
# The UI is loaded from ui/profiletool.ui, and resources.py is bundled.
PLUGINNAME := profiletool
PYTHON ?= python3
STAGE_DIR := build/$(PLUGINNAME)
ZIP_FILE := $(PLUGINNAME).zip
QGIS_PLUGIN_DIR ?= $(HOME)/.local/share/QGIS/QGIS3/profiles/default/python/plugins

PLUGIN_FILES := __init__.py profileplugin.py metadata.txt README.md LICENSE resources.py resources.qrc
PLUGIN_DIRS := tools ui icons i18n profile_points dxfwrite pyqtgraph

.PHONY: all stage zip deploy clean

all: zip

stage:
	rm -rf "$(STAGE_DIR)"
	mkdir -p "$(STAGE_DIR)"
	cp $(PLUGIN_FILES) "$(STAGE_DIR)/"
	cp -R $(PLUGIN_DIRS) "$(STAGE_DIR)/"
	find "$(STAGE_DIR)" -type d -name '__pycache__' -prune -exec rm -rf {} +
	find "$(STAGE_DIR)" -type f -name '*.pyc' -delete

zip: stage
	rm -f "$(ZIP_FILE)"
	cd build && "$(PYTHON)" -m zipfile -c "../$(ZIP_FILE)" "$(PLUGINNAME)"

deploy: stage
	mkdir -p "$(QGIS_PLUGIN_DIR)"
	rm -rf "$(QGIS_PLUGIN_DIR)/$(PLUGINNAME)"
	cp -R "$(STAGE_DIR)" "$(QGIS_PLUGIN_DIR)/$(PLUGINNAME)"

clean:
	rm -rf "$(STAGE_DIR)" "$(ZIP_FILE)"
