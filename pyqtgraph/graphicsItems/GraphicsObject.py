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
        
    def itemChange(self, change, value):
        # QGIS 3.44's PyQt5 SIP bindings sometimes pass an opaque QVariant
        # for the already-completed parent/scene notifications. Their return
        # value is ignored by Qt; passing the QVariant through SIP again raises
        # a conversion error, including when calling QVariant.value().
        if (QT_LIB == 'PyQt5' and isinstance(value, QtCore.QVariant)
                and change in [self.GraphicsItemChange.ItemParentHasChanged,
                               self.GraphicsItemChange.ItemSceneHasChanged]):
            ret = None
        else:
            ret = super().itemChange(change, value)
        # Restore pyqtgraph's original PyQt5 SIP parent-item workaround.
        # SIP needs a base QGraphicsItem wrapper when Qt changes a parent.
        if QT_LIB == 'PyQt5' and change == self.GraphicsItemChange.ItemParentChange and isinstance(ret, QtWidgets.QGraphicsItem):
            from ..Qt import sip
            ret = sip.cast(ret, QtWidgets.QGraphicsItem)
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
