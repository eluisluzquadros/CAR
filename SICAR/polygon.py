from enum import Enum


class Polygon(str, Enum):
    AREA_PROPERTY = "AREA_IMOVEL"
    APPS = "APPS"
    NATIVE_VEGETATION = "VEGETACAO_NATIVA"
    CONSOLIDATED_AREA = "AREA_CONSOLIDADA"
    AREA_FALL = "AREA_POUSIO"
    HYDROGRAPHY = "HIDROGRAFIA"
    RESTRICTED_USE = "USO_RESTRITO"
    ADMINISTRATIVE_SERVICE = "SERVIDAO_ADMINISTRATIVA"
    LEGAL_RESERVE = "RESERVA_LEGAL"
