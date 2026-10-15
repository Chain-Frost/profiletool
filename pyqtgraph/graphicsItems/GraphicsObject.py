import warnings
from ..Qt import QT_LIB, QtCore, QtWidgets
from .GraphicsItem import GraphicsItem

__all__ = ['GraphicsObject']
class GraphicsObject(GraphicsItem, QtWidgets.QGraphicsObject):
    """
    **Bases:** :class:`GraphicsItem <pyqtgraph.GraphicsItem>`, :class:`QtWidgets.QGraphicsObject`

    Extension of QGraphicsObject with some useful methods (provided by :class:`GraphicsItem <pyqtgraph.GraphicsItem>`)
    """
    _qtBaseClass = QtWidgets.QGraphicsObject
    def __init__(self, *args):
        self.__inform_view_on_changes = True
        QtWidgets.QGraphicsObject.__init__(self, *args)
        self.setFlag(self.GraphicsItemFlag.ItemSendsGeometryChanges)
        GraphicsItem.__init__(self)
        if QT_LIB == 'PyQt5':
            # QGIS 3.44/PyQt5 cannot round-trip QVariant wrappers for parent
            # and scene pointers through a Python itemChange() override.
            # Mirror the view-registration and bounds invalidation callbacks
            # through QGraphicsObject's native Qt property signals instead.
            # Access the parent's parentChanged signal explicitly: the
            # GraphicsItem mixin also defines a legacy parentChanged method.
            QtWidgets.QGraphicsObject.parentChanged.__get__(self, type(self)).connect(self.changeParent)
            self.xChanged.connect(self.informViewBoundsChanged)
            self.yChanged.connect(self.informViewBoundsChanged)
            self.rotationChanged.connect(self.informViewBoundsChanged)
            self.scaleChanged.connect(self.informViewBoundsChanged)
            self.transformOriginPointChanged.connect(self.informViewBoundsChanged)

    if QT_LIB == 'PyQt5':
        def setTransform(self, transform, combine=False):
            # An explicit matrix change does not emit x/rotation/scale signals.
            # Notify auto-range without restoring the unsafe Qt5 itemChange().
            QtWidgets.QGraphicsObject.setTransform(self, transform, combine)
            self.informViewBoundsChanged()

        def resetTransform(self):
            QtWidgets.QGraphicsObject.resetTransform(self)
            self.informViewBoundsChanged()
        
    def itemChange(self, change, value):
        ret = super().itemChange(change, value)
        if change in [self.GraphicsItemChange.ItemParentHasChanged, self.GraphicsItemChange.ItemSceneHasChanged]:
            if self.__class__.__dict__.get('parentChanged') is not None:
                # user's GraphicsObject subclass has a parentChanged() method
                warnings.warn(
                    "parentChanged() is deprecated and will be removed in the future. "
                    "Use changeParent() instead.",
                    DeprecationWarning, stacklevel=2
                )
                if QT_LIB == 'PySide6' and QtCore.__version_info__ == (6, 2, 2):
                    # workaround PySide6 6.2.2 issue https://bugreports.qt.io/browse/PYSIDE-1730
                    # note that the bug exists also in PySide6 6.2.2.1 / Qt 6.2.2
                    getattr(self.__class__, 'parentChanged')(self)
                else:
                    self.parentChanged()
            else:
                self.changeParent()
        try:
            inform_view_on_change = self.__inform_view_on_changes
        except AttributeError:
            # It's possible that the attribute was already collected when the itemChange happened
            # (if it was triggered during the gc of the object).
            pass
        else:
            if inform_view_on_change and change in [self.GraphicsItemChange.ItemPositionHasChanged, self.GraphicsItemChange.ItemTransformHasChanged]:
                self.informViewBoundsChanged()
            
        return ret


if QT_LIB == 'PyQt5':
    # Keep the native Qt virtual method for Qt5. Its QVariant arguments can
    # contain scene/item pointers which SIP cannot convert to Python. Removing
    # the Python override avoids corrupting the parent/scene change request.
    # Qt6 retains the original itemChange() implementation above.
    del GraphicsObject.itemChange
