from pandas import DataFrame
from FMT import Core
from pathlib import Path
from pandas import read_excel
from Interpretor import Interpretor
from YieldCreator import YieldCreator

class Bernier(YieldCreator):
    def __init__(self,p_model : Interpretor)->None:
        EXCEL_PATH  = Path("Bernier/Facteurs_Bernier_composition_âge.xlsx")
        super().__init__(p_model.get_themes())
        BERNIER_DATA = read_excel(EXCEL_PATH)
        self.m__bernier_yields = self.__create_yields(BERNIER_DATA,p_model)
    def __get_dataframe_max(dataframe : DataFrame):
        max_value = 0.0
        for DATA_COLUMN in dataframe:
            MAX_COL = dataframe[DATA_COLUMN].max()
            if isinstance(MAX_COL, float):
                max_value = max(MAX_COL,max_value)
        return max_value
    def get_factors(self)->[Core.FMTageyieldhandler]:
        return self.m__bernier_yields
    def __create_yields(self,dataframe : DataFrame, p_model : Interpretor)->[Core.FMTageyieldhandler]:
        AGGREGATES_TO_FIT = {"Résineux":"FCTCU_R",
                                "Résineux mixte":"FCTCU_MR",
                                "Feuillu mixte":"FCTCU_MF",
                                "Feuillu":"FCTCU_F"}
        YIELD_NAME = "yFactBr"
        MAX_VALUE = Bernier.__get_dataframe_max(dataframe)
        mask_list = self._create_empty_mask_list()
        for INDEX,ROW in dataframe.iterrows():
            ATTRIBUTE = AGGREGATES_TO_FIT[ROW["Ratio_selection"]]
            mask_list[4] = ATTRIBUTE
            newYield = self._create_age_yield(mask_list)
            BASES = list(range(0,Interpretor.get_max_age()))
            DATA = [0.0] * Interpretor.get_max_age()
            for DATA_COLUMN in dataframe:
                if DATA_COLUMN != "Ratio_selection":
                    DIVIDED = DATA_COLUMN.split("_")
                    if "+" in DATA_COLUMN:
                        DIVIDED[0]=DIVIDED[0].replace("+",'')
                        DIVIDED.append(Interpretor.get_max_age() * Interpretor.get_time_step() - 1)
                    LOWER = int(1+(int(DIVIDED[0]) / Interpretor.get_time_step()))
                    UPPER = int(int(DIVIDED[1]) / Interpretor.get_time_step())
                    if UPPER >= LOWER:
                        VALUE = ROW[DATA_COLUMN]
                        for index in range(LOWER,UPPER+1):
                            DATA[index] = (VALUE / MAX_VALUE)
            YieldCreator.append_to_yield(newYield,YIELD_NAME,BASES,DATA)