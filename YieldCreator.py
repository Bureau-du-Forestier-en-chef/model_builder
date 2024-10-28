from pandas import DataFrame,Series
from FMT import Core

class YieldCreator:
    def __init__(self,p_themes:[Core.FMTtheme])->None:
        self.m__themes = p_themes
    def __get_themes(self)->[Core.FMTtheme]:
        return self.m__themes
    def _create_age_yield(self,p_mask : [str])->Core.FMTageyieldhandler:
        return Core.FMTageyieldhandler(Core.FMTmask(" ".join(p_mask),self.__get_themes()))
    def _create_time_yield(self,p_mask : [str])->Core.FMTtimeyieldhandler:
        return Core.FMTageyieldhandler(Core.FMTmask(" ".join(p_mask),self.__get_themes()))
    def append_to_yield(p_yield,
                        p_yield_name: str,
                        p_bases : [int],
                        p_values: [float])->None:
       p_yield.setyieldvalues(p_yield_name,p_bases,p_values)
    def dataframe_to_time_yield(self,p_dataframe : DataFrame,
                                p_masks_columns:[str],
                                p_themes_index:[int],
                                p_period_column : str,
                                p_value_column : str,
                                p_yield_column: str)->[Core.FMTtimeyieldhandler]:
        MASK_LIST = self._create_empty_mask_list()
        yield_data = {} #Dictionnary of mask with data per period
        for i, ROW in p_dataframe.iterrows():
            MASK_STR = self.__get_mask_str_from_row(ROW,MASK_LIST,p_masks_columns,p_themes_index)
            if MASK_STR not in yield_data:
                yield_data[MASK_STR] = {}
            PERIOD = ROW[p_period_column]
            YIELD = ROW[p_yield_column]
            VALUE = ROW[p_value_column]
            if YIELD not in yield_data[MASK_STR]:
                yield_data[MASK_STR][YIELD] = {}
            yield_data[MASK_STR][YIELD][PERIOD] = VALUE
        new_yields = []
        for MASK in sorted(yield_data.keys()):
            new_yield=self._create_time_yield(MASK)
            for YIELD in sorted(yield_data[MASK].keys()):
                PERIODS = sorted(yield_data[MASK][YIELD].keys())
                values = []
                for PERIOD in PERIODS:
                    values.append(yield_data[MASK][YIELD][PERIOD])
                YieldCreator.append_to_yield(new_yield,YIELD,PERIODS,values)
            new_yields.append(new_yield)
        return new_yields
    def _create_empty_mask_list(self)->[str]:
        return ["?" for theme in self.__get_themes()]
    def __get_mask_str_from_row(self,p_row : Series,
                    p_mask_list: [str],
                    p_masks_columns:[str],
                    p_themes_index:[int])->str:
        for COLUMN,INDEX in zip(p_masks_columns,p_themes_index):
            p_mask_list[INDEX] = p_row[COLUMN]
        return ' '.join(p_mask_list)