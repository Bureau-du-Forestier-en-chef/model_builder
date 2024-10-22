from FMT import Core

class ThemeCreator:
    def __init__(self) -> None:
        pass
    def get_aggregates_to(p_theme:Core.FMTtheme,
                                p_new_aggregates:{str:[str]})->Core.FMTtheme:
        START = p_theme.getstart()
        ID = p_theme.getid()
        ATTRIBUTE_NAMES = p_theme.getattributenames()
        ATTRIBUTES = p_theme.getattributes("?")
        NAME = p_theme.getname()
        full_aggregates = []
        aggregates = p_theme.getaggregates()
        for AGGREGATE in aggregates:
            full_aggregates.append(p_theme.getattributes(AGGREGATE))
        for NEW_AGGREGATE in sorted(p_new_aggregates.keys()):
            aggregate_attributs = []
            for ATTRIBUTE in p_new_aggregates[NEW_AGGREGATE]:
                if ATTRIBUTE in ATTRIBUTES:
                    aggregate_attributs.append(ATTRIBUTE)
            aggregates.append(NEW_AGGREGATE)
            full_aggregates.append(aggregate_attributs)
        return Core.FMTtheme(ATTRIBUTES,ATTRIBUTE_NAMES,aggregates,full_aggregates,ID,START,NAME)