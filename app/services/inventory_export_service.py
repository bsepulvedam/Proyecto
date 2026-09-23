from datetime import datetime
from io import BytesIO
import re

from openpyxl import Workbook

from app.models.movimiento_inventario import MovimientoInventario

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
FORMULA_PREFIXES = ("=", "+", "-", "@")
ILLEGAL_XML_CHARACTERS = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F]")


def safe_excel_text(value: object) -> object:
    if isinstance(value, str):
        cleaned = ILLEGAL_XML_CHARACTERS.sub(" ", value)
        if cleaned.lstrip().startswith(FORMULA_PREFIXES):
            return f"'{cleaned}"
        return cleaned
    return value


def _append_safe(worksheet, values) -> None:
    worksheet.append(tuple(safe_excel_text(value) for value in values))


def build_movements_xlsx(movements: list[MovimientoInventario]) -> bytes:
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("Movimientos")
    _append_safe(
        sheet,
        (
            "Fecha",
            "N° documento",
            "Tipo",
            "Empresa",
            "SKU",
            "Producto",
            "Cantidad",
            "Unidad",
            "Costo unitario",
            "Valor total línea",
            "Guía despacho",
            "Entregado a",
            "Comuna",
            "Referencia",
            "Observaciones",
            "Observación línea",
            "Origen",
            "Actor / referencia",
            "Registrado el",
        ),
    )
    for movement in movements:
        for line in movement.detalles:
            _append_safe(
                sheet,
                (
                    movement.fecha,
                    movement.numero_documento,
                    movement.tipo,
                    movement.empresa.codigo,
                    line.producto.sku,
                    line.producto.nombre,
                    line.cantidad_presentaciones,
                    line.unidad_presentacion_snapshot,
                    line.costo_unitario,
                    line.valor_total,
                    movement.guia_despacho,
                    movement.entregado_a,
                    movement.comuna,
                    movement.referencia,
                    movement.observaciones,
                    line.observacion_linea,
                    movement.origen,
                    movement.actor_referencia,
                    movement.created_at.replace(tzinfo=None) if movement.created_at else None,
                ),
            )
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def movements_export_filename() -> str:
    return f"movimientos_inventario_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
