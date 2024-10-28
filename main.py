from Interpretor import Interpretor
from YieldCreator import YieldCreator
from ThemeCreator import ThemeCreator
from Bernier import Bernier
from pathlib import Path
from pandas import read_excel


def main():
    MODEL_LOCATION = Path("D:/CC_modele_feu/WS_CC/Feux_2023_ouest_V01.pri")
    SCENARIO = "strategique_AllEnrqc"
    MODEL_INTERPRETOR = Interpretor(MODEL_LOCATION,SCENARIO)
    BERNIER_YIELDS = Bernier(MODEL_INTERPRETOR)
    YIELDS_DATA_PATH = Path('T:/Donnees/02_Courant/07_Outil_moyen_methode/02_Innovation/02_CC/SimulationBorealeCC/04_productivite/03_ResultatsPreliminaires/20240705_modificateurs_moyens_SPAAD1/SDOM/Modificateurs_moyens_Volume_SDOM.xlsx')


    """ YIELDS_CLASSIFIER = Path()
    YIELDS_DATA = read_excel(YIELDS_DATA_PATH)
    Periods = {year : period for year,period in zip(range(2020,2300,5),range(1,90))}
    YIELDS_DATA['annee'].replace(Periods, inplace=True)
    YIELDS_NAME = {"AUT":"yV_G_gFi","Fi":"yV_G_gFi","Ft":"yV_G_gFt",
                   "Ri":"yV_G_gR","Rt":"yV_G_gR","Sb":"yV_E_SAB","TOT":"yv_s"}
    YIELDS_DATA['Ess_Groupe'].replace(YIELDS_NAME, inplace=True)
    print(YIELDS_DATA)
    YIELDS_TO_AGGREGATES = {"yV_E_SAB":"SAB",
                            "yV_G_gEpx":"EPX",
                            "yV_G_gBp":"BP",
                            "yV_G_gFi":"FI",
                            "yV_G_gPg":"PG"}
    THEME_ID = 4
    group = MODEL_INTERPRETOR.get_yields_by_value(YIELDS_TO_AGGREGATES.keys(),THEME_ID)
    for i,j in YIELDS_TO_AGGREGATES.items():
        LINK_NAME =i.upper()
        group[j] = group[LINK_NAME]
        del group[LINK_NAME]
    themes = MODEL_INTERPRETOR.get_themes()
    themes[THEME_ID] = ThemeCreator.get_aggregates_to(themes[THEME_ID],group)
    YIELD_CREATOR = YieldCreator(themes[THEME_ID]) """
    #NEW_TIME_YIELDS = YIELD_CREATOR.dataframe_to_time_yield(YIELDS_DATA,["g_strate"],[4],"annee","modif","Ess_Groupe")
    #print(NEW_TIME_YIELDS)
    return 0

if __name__ == "__main__":
    main()