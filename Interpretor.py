from FMT import Parser,Core
from FMT import Exception as FMTexception
from pathlib import Path
from pandas import DataFrame

class Interpretor:
    m_MAX_AGE = 30
    m_MAX_PERIOD = 30
    def __init__(self,p_primary:Path,p_scenario:str):
        modelParser = Parser.FMTmodelparser()
        modelParser.seterrorstowarnings([FMTexception.FMTexc.FMToutput_too_much_operator,
                                     FMTexception.FMTexc.FMToveridedyield,
                                     FMTexception.FMTexc.FMTdeathwithlock,
                                     FMTexception.FMTexc.FMTinvalid_geometry,
                                     FMTexception.FMTexc.FMTmissingyield,
                                     FMTexception.FMTexc.FMTsourcetotarget_transition,
                                     FMTexception.FMTexc.FMTsame_transitiontargets])
        scenarios = [p_scenario]
        self.m_MODEL = modelParser.readproject(str(p_primary), scenarios)[0]
    def get_themes(self)->[Core.FMTtheme]:
        return self.m_MODEL.getthemes()
    def get_yields_by_value(self,p_yields : [str],p_theme_index:int)->{str:str}:
        THEMES = self.m_MODEL.getthemes()
        YIELDS = self.m_MODEL.getyields()
        THEME_VALUES = THEMES[p_theme_index].getattributes("?")
        UPPER_YIELDS = [yld_name.upper() for yld_name in p_yields]
        MASK_LIST = ["?" for THEME in THEMES]
        returned = {yield_name : [] for yield_name in UPPER_YIELDS}
        for ATTRIBUTE in THEME_VALUES:
            MASK_LIST[p_theme_index] = ATTRIBUTE
            MASK = Core.FMTmask(" ".join(MASK_LIST),THEMES)
            values = {yield_name : 0.0 for yield_name in UPPER_YIELDS}
            for AGE in range(0,Interpretor.m_MAX_AGE+1):
                DEV = Core.FMTactualdevelopment(MASK,AGE,0,1.0)
                REQUEST = DEV.getyieldrequest()
                for YIELD_NAME in UPPER_YIELDS:
                    values[YIELD_NAME]+=YIELDS.get(REQUEST,YIELD_NAME)
            max_value = 0.0
            max_yield = ""
            for YIELD,VALUE in values.items():
                if VALUE >= max_value:
                    max_value = VALUE
                    max_yield  = YIELD
            returned[max_yield].append(ATTRIBUTE)
        return returned
    def get_yields_by_data(self,p_attributes : [str],p_theme_index:int,p_dataFrame : DataFrame):
        THEMES = self.m_MODEL.getthemes()
        YIELDS = self.m_MODEL.getyields()
        MASK_LIST = ["?" for THEME in THEMES]
        YIELD_NAME = p_dataFrame.name
        base_columns = [name for name in p_dataFrame.columns if column != 'AGE']
        returned = {name : [] for name in base_columns}
        for ATTRIBUTE in p_attributes:
            MASK_LIST[p_theme_index] = ATTRIBUTE
            MASK = Core.FMTmask(" ".join(MASK_LIST),THEMES)
            columns = base_columns[:]
            for INDEX, ROW in p_dataFrame.iterrows():
                DEV = Core.FMTactualdevelopment(MASK,int(ROW['AGE']),0,1.0)
                REQUEST = DEV.getyieldrequest()
                VALUE = YIELDS.get(REQUEST,YIELD_NAME)
                new_columns= []
                for column in columns:
                    if VALUE>=ROW[column]:
                        new_columns.append(column)
                columns = new_columns
            if columns:
                returned[columns[-1]].append(ATTRIBUTE)
        return returned
        
            