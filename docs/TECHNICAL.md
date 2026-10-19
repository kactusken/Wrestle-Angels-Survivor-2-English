# Technical notes - Wrestle Angels: Survivor 2

**Conventions:** numbers in hex with `0x`; addresses are RAM addresses unless marked as file
offsets; `u16`/`u32` little-endian unless marked BE. Findings are marked *verified in game* or
*from the code*.

## Contents
- [Image](#image) · [Disc layout](#disc-layout) · [Executable and memory](#executable-and-memory)
- [Archives and compression](#archives-and-compression) · [Text](#text) · [Images](#images)
- [Open questions](#open-questions)

## Image
`Wrestle Angels Survivor 2 (Japan).iso`, 4074340352 bytes, SHA-1 `ea5d4f86102205b885e15a09b5e4d4318d839136`.

## Disc layout
| LBA | Size | File | Contents |
|---|---|---|---|
| 894 | 57 | `/SYSTEM.CNF` |  |
| 895 | 3799136 | `/SLPM_550.56` |  |
| 11500 | 278353 | `/IOPRP310.IMG` |  |
| 11636 | 313669 | `/IRX.BIN` |  |
| 1000000 | 312768 | `/SYS/BEL.BIN` |  |
| 1000153 | 1776352 | `/SYS/BELT.DAT` |  |
| 1001021 | 22672160 | `/SYS/BG.BIN` |  |
| 1012092 | 64008 | `/SYS/BRINGR.GSL` |  |
| 1012124 | 339264 | `/SYS/CGMODE1.GSL` |  |
| 1012290 | 220480 | `/SYS/CGMODE2.GSL` |  |
| 1012398 | 271424 | `/SYS/CGMODE3.GSL` |  |
| 1012531 | 0 | `/SYS/CGMODE4.GSL` |  |
| 1012532 | 0 | `/SYS/CGMODE5.GSL` |  |
| 1012533 | 16960 | `/SYS/CGMODE6.GSL` |  |
| 1012542 | 254464 | `/SYS/CGMODE7.GSL` |  |
| 1012667 | 67904 | `/SYS/CGMODE8.GSL` |  |
| 1012701 | 28960 | `/SYS/CMTRN.GSL` |  |
| 1012716 | 226592 | `/SYS/COMBACK.GSL` |  |
| 1012827 | 80544 | `/SYS/COMSE.HBS` |  |
| 1012867 | 17696 | `/SYS/COM_P2.GSL` |  |
| 1012876 | 1200 | `/SYS/COM_P2C.GSL` |  |
| 1012877 | 288032 | `/SYS/CRI.GSL` |  |
| 1013018 | 247816 | `/SYS/DIR_A.GSL` |  |
| 1013140 | 247816 | `/SYS/DIR_B.GSL` |  |
| 1013262 | 3632 | `/SYS/ETC_CLUT.BIN` |  |
| 1013264 | 263933216 | `/SYS/EV.BIN` |  |
| 1142138 | 1698356 | `/SYS/FONT.BIN` |  |
| 1142968 | 9504 | `/SYS/FONTCLUT.GSL` |  |
| 1142973 | 305536 | `/SYS/GALETC.BIN` |  |
| 1143123 | 2911520 | `/SYS/GM_CHR.BIN` |  |
| 1144545 | 25656608 | `/SYS/GM_EYES.BIN` |  |
| 1157073 | 66848 | `/SYS/GYM_M.GSL` |  |
| 1157106 | 19744 | `/SYS/G_BUTTON.GSL` |  |
| 1157116 | 4480 | `/SYS/G_MENU0.GSL` |  |
| 1157119 | 6496 | `/SYS/G_MENU1.GSL` |  |
| 1157123 | 13600 | `/SYS/G_MENU2.GSL` |  |
| 1157130 | 9376 | `/SYS/G_MENU3.GSL` |  |
| 1157135 | 8032 | `/SYS/G_MENU4.GSL` |  |
| 1157139 | 7456 | `/SYS/G_MENU5.GSL` |  |
| 1157143 | 33112 | `/SYS/ICON.ICO` |  |
| 1157160 | 288032 | `/SYS/MAP.GSL` |  |
| 1157301 | 66848 | `/SYS/MA_HIS00.GSL` |  |
| 1157334 | 66848 | `/SYS/MENU.GSL` |  |
| 1157367 | 34080 | `/SYS/MENU1.GSL` |  |
| 1157384 | 4512 | `/SYS/MENUWIN.GSL` |  |
| 1157387 | 450464 | `/SYS/MMAKE3.GSL` |  |
| 1157607 | 20544 | `/SYS/MODE.GSL` |  |
| 1157618 | 66848 | `/SYS/MSG_ETC.GSL` |  |
| 1157651 | 72992 | `/SYS/MSG_WIN.GSL` |  |
| 1157687 | 216352 | `/SYS/NAMEBACK.GSL` |  |
| 1157793 | 9504 | `/SYS/NAME_1.GSL` |  |
| 1157798 | 27936 | `/SYS/NAME_2.GSL` |  |
| 1157812 | 132384 | `/SYS/OFFICEUE.GSL` |  |
| 1157877 | 308512 | `/SYS/OMA_BG00.GSL` |  |
| 1158028 | 594592 | `/SYS/OPTION.BIN` |  |
| 1158319 | 288032 | `/SYS/OP_TBG00.GSL` |  |
| 1158460 | 593648 | `/SYS/REPORTS.GSL` |  |
| 1158750 | 476352 | `/SYS/SLFILE.BIN` |  |
| 1158983 | 226592 | `/SYS/ST.GSL` |  |
| 1159094 | 226592 | `/SYS/STC_00.GSL` |  |
| 1159205 | 22944 | `/SYS/STC_P.GSL` |  |
| 1159217 | 226592 | `/SYS/STD_00.GSL` |  |
| 1159328 | 9504 | `/SYS/STR_P0.GSL` |  |
| 1159333 | 66848 | `/SYS/ST_00A.GSL` |  |
| 1159366 | 66848 | `/SYS/ST_01A.GSL` |  |
| 1159399 | 19024 | `/SYS/ST_02A.GSL` |  |
| 1159409 | 77344 | `/SYS/ST_04A.GSL` |  |
| 1159447 | 226592 | `/SYS/ST_05.GSL` |  |
| 1159558 | 226592 | `/SYS/ST_05B.GSL` |  |
| 1159669 | 288032 | `/SYS/ST_06.GSL` |  |
| 1159810 | 288032 | `/SYS/ST_06B.GSL` |  |
| 1159951 | 288032 | `/SYS/ST_06C.GSL` |  |
| 1160092 | 66848 | `/SYS/ST_07A.GSL` |  |
| 1160125 | 216352 | `/SYS/ST_AWI01.GSL` |  |
| 1160231 | 8992 | `/SYS/ST_BK.GSL` |  |
| 1160236 | 66848 | `/SYS/ST_UP.GSL` |  |
| 1160269 | 288032 | `/SYS/SUCCESS.GSL` |  |
| 1160410 | 57120 | `/SYS/SYSTEM.GSL` |  |
| 1160438 | 368992 | `/SYS/SYSTITLE.GSL` |  |
| 1160619 | 34080 | `/SYS/S_MENU01.GSL` |  |
| 1160636 | 34080 | `/SYS/S_MENU02.GSL` |  |
| 1160653 | 34080 | `/SYS/S_MENU05.GSL` |  |
| 1160670 | 34080 | `/SYS/S_MENU06.GSL` |  |
| 1160687 | 34080 | `/SYS/S_MENU07.GSL` |  |
| 1160704 | 115040 | `/SYS/TH01.GSL` |  |
| 1160761 | 115040 | `/SYS/TH02.GSL` |  |
| 1160818 | 115040 | `/SYS/TH03.GSL` |  |
| 1160875 | 115040 | `/SYS/TH04.GSL` |  |
| 1160932 | 115040 | `/SYS/TH05.GSL` |  |
| 1160989 | 115040 | `/SYS/TH06.GSL` |  |
| 1161046 | 115040 | `/SYS/TH07.GSL` |  |
| 1161103 | 115040 | `/SYS/TH08.GSL` |  |
| 1161160 | 115040 | `/SYS/TH09.GSL` |  |
| 1161217 | 115040 | `/SYS/TH10.GSL` |  |
| 1161274 | 115040 | `/SYS/TH11.GSL` |  |
| 1161331 | 115040 | `/SYS/TH12.GSL` |  |
| 1161388 | 115040 | `/SYS/TH13.GSL` |  |
| 1161445 | 115040 | `/SYS/TH14.GSL` |  |
| 1161502 | 115040 | `/SYS/TH15.GSL` |  |
| 1161559 | 115040 | `/SYS/TH16.GSL` |  |
| 1161616 | 115040 | `/SYS/TH17.GSL` |  |
| 1161673 | 115040 | `/SYS/TH18.GSL` |  |
| 1161730 | 115040 | `/SYS/TH19.GSL` |  |
| 1161787 | 115040 | `/SYS/TH20.GSL` |  |
| 1161844 | 115040 | `/SYS/TH21.GSL` |  |
| 1161901 | 115040 | `/SYS/TH22.GSL` |  |
| 1161958 | 115040 | `/SYS/TH23.GSL` |  |
| 1162015 | 115040 | `/SYS/TH24.GSL` |  |
| 1162072 | 115040 | `/SYS/TH25.GSL` |  |
| 1162129 | 115040 | `/SYS/TH26.GSL` |  |
| 1162186 | 115040 | `/SYS/TH27.GSL` |  |
| 1162243 | 115040 | `/SYS/TH28.GSL` |  |
| 1162300 | 115040 | `/SYS/TH29.GSL` |  |
| 1162357 | 115040 | `/SYS/TH30.GSL` |  |
| 1162414 | 115040 | `/SYS/TH31.GSL` |  |
| 1162471 | 115040 | `/SYS/TH32.GSL` |  |
| 1162528 | 115040 | `/SYS/TH33.GSL` |  |
| 1162585 | 115040 | `/SYS/TH34.GSL` |  |
| 1162642 | 115040 | `/SYS/TH35.GSL` |  |
| 1162699 | 115040 | `/SYS/TH36.GSL` |  |
| 1162756 | 132384 | `/SYS/TITLE.GSL` |  |
| 1162821 | 288032 | `/SYS/TRYFIST.GSL` |  |
| 1162962 | 288032 | `/SYS/WARNING.GSL` |  |
| 1163103 | 6037504 | `/BGM/BGM01.ADX` |  |
| 1166051 | 5486592 | `/BGM/BGM02.ADX` |  |
| 1168730 | 6123520 | `/BGM/BGM03.ADX` |  |
| 1171720 | 6342656 | `/BGM/BGM04.ADX` |  |
| 1174817 | 5447680 | `/BGM/BGM05.ADX` |  |
| 1177477 | 4644864 | `/BGM/BGM06.ADX` |  |
| 1179745 | 5853184 | `/BGM/BGM07.ADX` |  |
| 1182603 | 6475776 | `/BGM/BGM08.ADX` |  |
| 1185765 | 4341760 | `/BGM/BGM09.ADX` |  |
| 1187885 | 5693440 | `/BGM/BGM10.ADX` |  |
| 1190665 | 5591040 | `/BGM/BGM11.ADX` |  |
| 1193395 | 5191680 | `/BGM/BGM12.ADX` |  |
| 1195930 | 5896192 | `/BGM/BGM13.ADX` |  |
| 1198809 | 7010304 | `/BGM/BGM14.ADX` |  |
| 1202232 | 6320128 | `/BGM/BGM15.ADX` |  |
| 1205318 | 5562368 | `/BGM/BGM16.ADX` |  |
| 1208034 | 5189632 | `/BGM/BGM17.ADX` |  |
| 1210568 | 6881280 | `/BGM/BGM18.ADX` |  |
| 1213928 | 16337902 | `/BGM/BGM19.ADX` |  |
| 1221906 | 2709310 | `/BGM/BGM20.ADX` |  |
| 1223229 | 900636 | `/BGM/SE.ACX` |  |
| 1223669 | 10174464 | `/BGM/SE.AFS` |  |
| 1228637 | 868839424 | `/BGM/VOICE.AFS` |  |
| 1652875 | 3954688 | `/BGM2/BGM31.ADX` |  |
| 1654806 | 4087808 | `/BGM2/BGM32.ADX` |  |
| 1656802 | 4700160 | `/BGM2/BGM33.ADX` |  |
| 1659097 | 4810752 | `/BGM2/BGM34.ADX` |  |
| 1661446 | 5050368 | `/BGM2/BGM35.ADX` |  |
| 1663912 | 5165056 | `/BGM2/BGM36.ADX` |  |
| 1666434 | 4061184 | `/BGM2/BGM37.ADX` |  |
| 1668417 | 5005312 | `/BGM2/BGM38.ADX` |  |
| 1670861 | 4282368 | `/BGM2/BGM39.ADX` |  |
| 1672952 | 4575232 | `/BGM2/BGM40.ADX` |  |
| 1675186 | 3721216 | `/BGM2/BGM41.ADX` |  |
| 1677003 | 4536320 | `/BGM2/BGM42.ADX` |  |
| 1679218 | 4065280 | `/BGM2/BGM43.ADX` |  |
| 1681203 | 3981312 | `/BGM2/BGM44.ADX` |  |
| 1683147 | 5353472 | `/BGM2/BGM45.ADX` |  |
| 1685761 | 4804608 | `/BGM2/BGM46.ADX` |  |
| 1688107 | 3911680 | `/BGM2/BGM47.ADX` |  |
| 1690017 | 4974592 | `/BGM2/BGM48.ADX` |  |
| 1692446 | 91717636 | `/BGM2/WAS2.PSS` |  |
| 1737231 | 66848 | `/EVE/EVENT_A.GSL` |  |
| 1737264 | 66848 | `/EVE/EVENT_C.GSL` |  |
| 1737297 | 66848 | `/EVE/EVENT_E.GSL` |  |
| 1737330 | 66848 | `/EVE/EVENT_N.GSL` |  |
| 1737363 | 66848 | `/EVE/SINJIN_S.GSL` |  |
| 1737396 | 66848 | `/EVE/SINJIN_T.GSL` |  |
| 1737429 | 34080 | `/MAP/DANTAI.GSL` |  |
| 1737446 | 34080 | `/MAP/GOODS.GSL` |  |
| 1737463 | 34080 | `/MAP/IN.GSL` |  |
| 1737480 | 34080 | `/MAP/KOUGYOU.GSL` |  |
| 1737497 | 263456 | `/MAP/MAP.GSL` |  |
| 1737626 | 66848 | `/MAP/MAP_ETC.GSL` |  |
| 1737659 | 2336 | `/MAP/MAP_ETC2.GSL` |  |
| 1737661 | 134928 | `/MAP/MAP_P.BIN` |  |
| 1737727 | 34080 | `/MAP/SAIDAI.GSL` |  |
| 1737744 | 263456 | `/MAP/WM_PARTS.GSL` |  |
| 1737873 | 84256 | `/MARK/MARKSEL1.GSL` |  |
| 1737915 | 125728 | `/MARK/MARKSEL2.GSL` |  |
| 1737977 | 17696 | `/MARK/OF_MAC00.GSL` |  |
| 1737986 | 17696 | `/MARK/OF_MAC01.GSL` |  |
| 1737995 | 17696 | `/MARK/OF_MAC02.GSL` |  |
| 1738004 | 17696 | `/MARK/OF_MAC03.GSL` |  |
| 1738013 | 17696 | `/MARK/OF_MAC04.GSL` |  |
| 1738022 | 17696 | `/MARK/OF_MAC05.GSL` |  |
| 1738031 | 17696 | `/MARK/OF_MAC06.GSL` |  |
| 1738040 | 17696 | `/MARK/OF_MAC07.GSL` |  |
| 1738049 | 17696 | `/MARK/OF_MAC08.GSL` |  |
| 1738058 | 17696 | `/MARK/OF_MAC09.GSL` |  |
| 1738067 | 17696 | `/MARK/OF_MAR00.GSL` |  |
| 1738076 | 17696 | `/MARK/OF_MAR01.GSL` |  |
| 1738085 | 17696 | `/MARK/OF_MAR02.GSL` |  |
| 1738094 | 17696 | `/MARK/OF_MAR03.GSL` |  |
| 1738103 | 17696 | `/MARK/OF_MAR04.GSL` |  |
| 1738112 | 17696 | `/MARK/OF_MAR05.GSL` |  |
| 1738121 | 17696 | `/MARK/OF_MAR06.GSL` |  |
| 1738130 | 17696 | `/MARK/OF_MAR07.GSL` |  |
| 1738139 | 288032 | `/MASK/MSK_001.GSL` |  |
| 1738280 | 288032 | `/MASK/MSK_002.GSL` |  |
| 1738421 | 288032 | `/MASK/MSK_003.GSL` |  |
| 1738562 | 288032 | `/MASK/MSK_004.GSL` |  |
| 1738703 | 288032 | `/MASK/MSK_005.GSL` |  |
| 1738844 | 288032 | `/MASK/MSK_006.GSL` |  |
| 1738985 | 288032 | `/MASK/MSK_007.GSL` |  |
| 1739126 | 288032 | `/MASK/MSK_008.GSL` |  |
| 1739267 | 288032 | `/MASK/MSK_009.GSL` |  |
| 1739408 | 288032 | `/MASK/MSK_010.GSL` |  |
| 1739549 | 288032 | `/MASK/MSK_011.GSL` |  |
| 1739690 | 288032 | `/MASK/MSK_012.GSL` |  |
| 1739831 | 288032 | `/MASK/MSK_013.GSL` |  |
| 1739972 | 288032 | `/MASK/MSK_014.GSL` |  |
| 1740113 | 288032 | `/MASK/MSK_015.GSL` |  |
| 1740254 | 288032 | `/MASK/MSK_016.GSL` |  |
| 1740395 | 288032 | `/MASK/MSK_017.GSL` |  |
| 1740536 | 288032 | `/MASK/MSK_018.GSL` |  |
| 1740677 | 288032 | `/MASK/MSK_019.GSL` |  |
| 1740818 | 288032 | `/MASK/MSK_020.GSL` |  |
| 1740959 | 288032 | `/MASK/MSK_021.GSL` |  |
| 1741100 | 288032 | `/MASK/MSK_022.GSL` |  |
| 1741241 | 288032 | `/MASK/MSK_023.GSL` |  |
| 1741382 | 288032 | `/MASK/MSK_024.GSL` |  |
| 1741523 | 288032 | `/MASK/MSK_025.GSL` |  |
| 1741664 | 288032 | `/MASK/MSK_026.GSL` |  |
| 1741805 | 288032 | `/MASK/MSK_027.GSL` |  |
| 1741946 | 288032 | `/MASK/MSK_028.GSL` |  |
| 1742087 | 288032 | `/MASK/MSK_029.GSL` |  |
| 1742228 | 288032 | `/MASK/MSK_030.GSL` |  |
| 1742369 | 288032 | `/MASK/MSK_031.GSL` |  |
| 1742510 | 288032 | `/MASK/MSK_032.GSL` |  |
| 1742651 | 288032 | `/MASK/MSK_033.GSL` |  |
| 1742792 | 288032 | `/MASK/MSK_034.GSL` |  |
| 1742933 | 288032 | `/MASK/MSK_035.GSL` |  |
| 1743074 | 288032 | `/MASK/MSK_036.GSL` |  |
| 1743215 | 288032 | `/MASK/MSK_037.GSL` |  |
| 1743356 | 288032 | `/MASK/MSK_038.GSL` |  |
| 1743497 | 288032 | `/MASK/MSK_039.GSL` |  |
| 1743638 | 288032 | `/MASK/MSK_040.GSL` |  |
| 1743779 | 288032 | `/MASK/MSK_041.GSL` |  |
| 1743920 | 288032 | `/MASK/MSK_042.GSL` |  |
| 1744061 | 288032 | `/MASK/MSK_043.GSL` |  |
| 1744202 | 288032 | `/MASK/MSK_044.GSL` |  |
| 1744343 | 288032 | `/MASK/MSK_045.GSL` |  |
| 1744484 | 288032 | `/MASK/MSK_046.GSL` |  |
| 1744625 | 288032 | `/MASK/MSK_047.GSL` |  |
| 1744766 | 288032 | `/MASK/MSK_048.GSL` |  |
| 1744907 | 288032 | `/MASK/MSK_101.GSL` |  |
| 1745048 | 288032 | `/MASK/MSK_102.GSL` |  |
| 1745189 | 288032 | `/MASK/MSK_103.GSL` |  |
| 1745330 | 288032 | `/MASK/MSK_104.GSL` |  |
| 1745471 | 44832 | `/PAR/MONTH01.GSL` |  |
| 1745493 | 44832 | `/PAR/MONTH02.GSL` |  |
| 1745515 | 44832 | `/PAR/MONTH03.GSL` |  |
| 1745537 | 44832 | `/PAR/MONTH04.GSL` |  |
| 1745559 | 44832 | `/PAR/MONTH05.GSL` |  |
| 1745581 | 44832 | `/PAR/MONTH06.GSL` |  |
| 1745603 | 44832 | `/PAR/MONTH07.GSL` |  |
| 1745625 | 44832 | `/PAR/MONTH08.GSL` |  |
| 1745647 | 44832 | `/PAR/MONTH09.GSL` |  |
| 1745669 | 44832 | `/PAR/MONTH10.GSL` |  |
| 1745691 | 44832 | `/PAR/MONTH11.GSL` |  |
| 1745713 | 44832 | `/PAR/MONTH12.GSL` |  |
| 1745735 | 333136 | `/PAR/PRT.BIN` |  |
| 1745898 | 17440 | `/PAR/SUBTIT00.GSL` |  |
| 1745907 | 17440 | `/PAR/SUBTIT01.GSL` |  |
| 1745916 | 17440 | `/PAR/SUBTIT02.GSL` |  |
| 1745925 | 17440 | `/PAR/SUBTIT03.GSL` |  |
| 1745934 | 17440 | `/PAR/SUBTIT04.GSL` |  |
| 1745943 | 17440 | `/PAR/SUBTIT05.GSL` |  |
| 1745952 | 17440 | `/PAR/SUBTIT06.GSL` |  |
| 1745961 | 17440 | `/PAR/SUBTIT07.GSL` |  |
| 1745970 | 17440 | `/PAR/SUBTIT08.GSL` |  |
| 1745979 | 17440 | `/PAR/SUBTIT09.GSL` |  |
| 1745988 | 17440 | `/PAR/SUBTIT10.GSL` |  |
| 1745997 | 17440 | `/PAR/SUBTIT11.GSL` |  |
| 1746006 | 17440 | `/PAR/SUBTIT12.GSL` |  |
| 1746015 | 17440 | `/PAR/SUBTIT13.GSL` |  |
| 1746024 | 17440 | `/PAR/SUBTIT14.GSL` |  |
| 1746033 | 17440 | `/PAR/SUBTIT15.GSL` |  |
| 1746042 | 17440 | `/PAR/SUBTIT16.GSL` |  |
| 1746051 | 85859 | `/SCR/001.BIN` |  |
| 1746093 | 86227 | `/SCR/002.BIN` |  |
| 1746136 | 88327 | `/SCR/003.BIN` |  |
| 1746180 | 85913 | `/SCR/004.BIN` |  |
| 1746222 | 83015 | `/SCR/005.BIN` |  |
| 1746263 | 87379 | `/SCR/006.BIN` |  |
| 1746306 | 87717 | `/SCR/007.BIN` |  |
| 1746349 | 87011 | `/SCR/008.BIN` |  |
| 1746392 | 83975 | `/SCR/009.BIN` |  |
| 1746434 | 86247 | `/SCR/010.BIN` |  |
| 1746477 | 85887 | `/SCR/011.BIN` |  |
| 1746519 | 85089 | `/SCR/012.BIN` |  |
| 1746561 | 87147 | `/SCR/013.BIN` |  |
| 1746604 | 86667 | `/SCR/014.BIN` |  |
| 1746647 | 94515 | `/SCR/015.BIN` |  |
| 1746694 | 85369 | `/SCR/016.BIN` |  |
| 1746736 | 84801 | `/SCR/017.BIN` |  |
| 1746778 | 85805 | `/SCR/018.BIN` |  |
| 1746820 | 89519 | `/SCR/019.BIN` |  |
| 1746864 | 83795 | `/SCR/020.BIN` |  |
| 1746905 | 87163 | `/SCR/021.BIN` |  |
| 1746948 | 89135 | `/SCR/022.BIN` |  |
| 1746992 | 84957 | `/SCR/023.BIN` |  |
| 1747034 | 85845 | `/SCR/024.BIN` |  |
| 1747076 | 85213 | `/SCR/025.BIN` |  |
| 1747118 | 86111 | `/SCR/026.BIN` |  |
| 1747161 | 86073 | `/SCR/027.BIN` |  |
| 1747204 | 82891 | `/SCR/028.BIN` |  |
| 1747245 | 86818 | `/SCR/029.BIN` |  |
| 1747288 | 81668 | `/SCR/030.BIN` |  |
| 1747328 | 83076 | `/SCR/031.BIN` |  |
| 1747369 | 82796 | `/SCR/032.BIN` |  |
| 1747410 | 86862 | `/SCR/033.BIN` |  |
| 1747453 | 83610 | `/SCR/034.BIN` |  |
| 1747494 | 87788 | `/SCR/035.BIN` |  |
| 1747537 | 82893 | `/SCR/036.BIN` |  |
| 1747578 | 83465 | `/SCR/037.BIN` |  |
| 1747619 | 85049 | `/SCR/038.BIN` |  |
| 1747661 | 93971 | `/SCR/039.BIN` |  |
| 1747707 | 88394 | `/SCR/040.BIN` |  |
| 1747751 | 86473 | `/SCR/041.BIN` |  |
| 1747794 | 92478 | `/SCR/042.BIN` |  |
| 1747840 | 85526 | `/SCR/043.BIN` |  |
| 1747882 | 91471 | `/SCR/044.BIN` |  |
| 1747927 | 92737 | `/SCR/045.BIN` |  |
| 1747973 | 90888 | `/SCR/046.BIN` |  |
| 1748018 | 87814 | `/SCR/047.BIN` |  |
| 1748061 | 83664 | `/SCR/048.BIN` |  |
| 1748102 | 88261 | `/SCR/049.BIN` |  |
| 1748146 | 88261 | `/SCR/050.BIN` |  |
| 1748190 | 88847 | `/SCR/051.BIN` |  |
| 1748234 | 86941 | `/SCR/052.BIN` |  |
| 1748277 | 84666 | `/SCR/053.BIN` |  |
| 1748319 | 82094 | `/SCR/054.BIN` |  |
| 1748360 | 85252 | `/SCR/055.BIN` |  |
| 1748402 | 84787 | `/SCR/056.BIN` |  |
| 1748444 | 85822 | `/SCR/057.BIN` |  |
| 1748486 | 85204 | `/SCR/058.BIN` |  |
| 1748528 | 84952 | `/SCR/059.BIN` |  |
| 1748570 | 85540 | `/SCR/060.BIN` |  |
| 1748612 | 82564 | `/SCR/061.BIN` |  |
| 1748653 | 85150 | `/SCR/062.BIN` |  |
| 1748695 | 84701 | `/SCR/063.BIN` |  |
| 1748737 | 79013 | `/SCR/064.BIN` |  |
| 1748776 | 88733 | `/SCR/065.BIN` |  |
| 1748820 | 83866 | `/SCR/066.BIN` |  |
| 1748861 | 84912 | `/SCR/067.BIN` |  |
| 1748903 | 81158 | `/SCR/068.BIN` |  |
| 1748943 | 84879 | `/SCR/069.BIN` |  |
| 1748985 | 87627 | `/SCR/070.BIN` |  |
| 1749028 | 88563 | `/SCR/071.BIN` |  |
| 1749072 | 86150 | `/SCR/072.BIN` |  |
| 1749115 | 85680 | `/SCR/073.BIN` |  |
| 1749157 | 88430 | `/SCR/074.BIN` |  |
| 1749201 | 87840 | `/SCR/075.BIN` |  |
| 1749244 | 81838 | `/SCR/076.BIN` |  |
| 1749284 | 84605 | `/SCR/077.BIN` |  |
| 1749326 | 82114 | `/SCR/078.BIN` |  |
| 1749367 | 83840 | `/SCR/079.BIN` |  |
| 1749408 | 87693 | `/SCR/101.BIN` |  |
| 1749451 | 88013 | `/SCR/102.BIN` |  |
| 1749494 | 88633 | `/SCR/103.BIN` |  |
| 1749538 | 87103 | `/SCR/104.BIN` |  |
| 1749581 | 84737 | `/SCR/105.BIN` |  |
| 1749623 | 89357 | `/SCR/106.BIN` |  |
| 1749667 | 85031 | `/SCR/107.BIN` |  |
| 1749709 | 89537 | `/SCR/108.BIN` |  |
| 1749753 | 85761 | `/SCR/109.BIN` |  |
| 1749795 | 85201 | `/SCR/110.BIN` |  |
| 1749837 | 82653 | `/SCR/111.BIN` |  |
| 1749878 | 85089 | `/SCR/112.BIN` |  |
| 1749920 | 87629 | `/SCR/113.BIN` |  |
| 1749963 | 86265 | `/SCR/114.BIN` |  |
| 1750006 | 92681 | `/SCR/115.BIN` |  |
| 1750052 | 87703 | `/SCR/116.BIN` |  |
| 1750095 | 84479 | `/SCR/117.BIN` |  |
| 1750137 | 84759 | `/SCR/118.BIN` |  |
| 1750179 | 88505 | `/SCR/119.BIN` |  |
| 1750223 | 86385 | `/SCR/120.BIN` |  |
| 1750266 | 86889 | `/SCR/121.BIN` |  |
| 1750309 | 90149 | `/SCR/122.BIN` |  |
| 1750354 | 87499 | `/SCR/123.BIN` |  |
| 1750397 | 86827 | `/SCR/124.BIN` |  |
| 1750440 | 87755 | `/SCR/125.BIN` |  |
| 1750483 | 88589 | `/SCR/126.BIN` |  |
| 1750527 | 85735 | `/SCR/127.BIN` |  |
| 1750569 | 85111 | `/SCR/128.BIN` |  |
| 1750611 | 87557 | `/SCR/129.BIN` |  |
| 1750654 | 82327 | `/SCR/130.BIN` |  |
| 1750695 | 85039 | `/SCR/131.BIN` |  |
| 1750737 | 84647 | `/SCR/132.BIN` |  |
| 1750779 | 89017 | `/SCR/133.BIN` |  |
| 1750823 | 86201 | `/SCR/134.BIN` |  |
| 1750866 | 89767 | `/SCR/135.BIN` |  |
| 1750910 | 83359 | `/SCR/136.BIN` |  |
| 1750951 | 83143 | `/SCR/137.BIN` |  |
| 1750992 | 83263 | `/SCR/138.BIN` |  |
| 1751033 | 92813 | `/SCR/139.BIN` |  |
| 1751079 | 90727 | `/SCR/140.BIN` |  |
| 1751124 | 87889 | `/SCR/141.BIN` |  |
| 1751167 | 94361 | `/SCR/142.BIN` |  |
| 1751214 | 86121 | `/SCR/143.BIN` |  |
| 1751257 | 90539 | `/SCR/144.BIN` |  |
| 1751302 | 92737 | `/SCR/145.BIN` |  |
| 1751348 | 90936 | `/SCR/146.BIN` |  |
| 1751393 | 89181 | `/SCR/147.BIN` |  |
| 1751437 | 85063 | `/SCR/148.BIN` |  |
| 1751479 | 87151 | `/SCR/149.BIN` |  |
| 1751522 | 87151 | `/SCR/150.BIN` |  |
| 1751565 | 87721 | `/SCR/151.BIN` |  |
| 1751608 | 84433 | `/SCR/152.BIN` |  |
| 1751650 | 85197 | `/SCR/153.BIN` |  |
| 1751692 | 84749 | `/SCR/154.BIN` |  |
| 1751734 | 87971 | `/SCR/155.BIN` |  |
| 1751777 | 82825 | `/SCR/156.BIN` |  |
| 1751818 | 87253 | `/SCR/157.BIN` |  |
| 1751861 | 87039 | `/SCR/158.BIN` |  |
| 1751904 | 86835 | `/SCR/159.BIN` |  |
| 1751947 | 87535 | `/SCR/160.BIN` |  |
| 1751990 | 83787 | `/SCR/161.BIN` |  |
| 1752031 | 87145 | `/SCR/162.BIN` |  |
| 1752074 | 86245 | `/SCR/163.BIN` |  |
| 1752117 | 78723 | `/SCR/164.BIN` |  |
| 1752156 | 87687 | `/SCR/165.BIN` |  |
| 1752199 | 86585 | `/SCR/166.BIN` |  |
| 1752242 | 86071 | `/SCR/167.BIN` |  |
| 1752285 | 83797 | `/SCR/168.BIN` |  |
| 1752326 | 83753 | `/SCR/169.BIN` |  |
| 1752367 | 85969 | `/SCR/170.BIN` |  |
| 1752409 | 86665 | `/SCR/171.BIN` |  |
| 1752452 | 87357 | `/SCR/172.BIN` |  |
| 1752495 | 87643 | `/SCR/173.BIN` |  |
| 1752538 | 89749 | `/SCR/174.BIN` |  |
| 1752582 | 89947 | `/SCR/175.BIN` |  |
| 1752626 | 83929 | `/SCR/176.BIN` |  |
| 1752667 | 85695 | `/SCR/177.BIN` |  |
| 1752709 | 83997 | `/SCR/178.BIN` |  |
| 1752751 | 85207 | `/SCR/179.BIN` |  |
| 1752793 | 5182 | `/SCR/201.BIN` |  |
| 1752796 | 5123 | `/SCR/202.BIN` |  |
| 1752799 | 5640 | `/SCR/203.BIN` |  |
| 1752802 | 5653 | `/SCR/204.BIN` |  |
| 1752805 | 5689 | `/SCR/205.BIN` |  |
| 1752808 | 5691 | `/SCR/206.BIN` |  |
| 1752811 | 6203 | `/SCR/207.BIN` |  |
| 1752815 | 6195 | `/SCR/208.BIN` |  |
| 1752819 | 5689 | `/SCR/209.BIN` |  |
| 1752822 | 5753 | `/SCR/210.BIN` |  |
| 1752825 | 6393 | `/SCR/211.BIN` |  |
| 1752829 | 5151 | `/SCR/212.BIN` |  |
| 1752832 | 5167 | `/SCR/213.BIN` |  |
| 1752835 | 5189 | `/SCR/214.BIN` |  |
| 1752838 | 5223 | `/SCR/215.BIN` |  |
| 1752841 | 5715 | `/SCR/216.BIN` |  |
| 1752844 | 4947 | `/SCR/217.BIN` |  |
| 1752847 | 5745 | `/SCR/218.BIN` |  |
| 1752850 | 5269 | `/SCR/219.BIN` |  |
| 1752853 | 6599 | `/SCR/220.BIN` |  |
| 1752857 | 5171 | `/SCR/221.BIN` |  |
| 1752860 | 5759 | `/SCR/222.BIN` |  |
| 1752863 | 5193 | `/SCR/223.BIN` |  |
| 1752866 | 5611 | `/SCR/224.BIN` |  |
| 1752869 | 5299 | `/SCR/225.BIN` |  |
| 1752872 | 5215 | `/SCR/226.BIN` |  |
| 1752875 | 5161 | `/SCR/227.BIN` |  |
| 1752878 | 5103 | `/SCR/228.BIN` |  |
| 1752881 | 5311 | `/SCR/229.BIN` |  |
| 1752884 | 5143 | `/SCR/230.BIN` |  |
| 1752887 | 5615 | `/SCR/231.BIN` |  |
| 1752890 | 5321 | `/SCR/232.BIN` |  |
| 1752893 | 5771 | `/SCR/233.BIN` |  |
| 1752896 | 5683 | `/SCR/234.BIN` |  |
| 1752899 | 5187 | `/SCR/235.BIN` |  |
| 1752902 | 5303 | `/SCR/236.BIN` |  |
| 1752905 | 5171 | `/SCR/237.BIN` |  |
| 1752908 | 5055 | `/SCR/238.BIN` |  |
| 1752911 | 5273 | `/SCR/239.BIN` |  |
| 1752914 | 5721 | `/SCR/240.BIN` |  |
| 1752917 | 5219 | `/SCR/241.BIN` |  |
| 1752920 | 5769 | `/SCR/242.BIN` |  |
| 1752923 | 5199 | `/SCR/301.BIN` |  |
| 1752926 | 5055 | `/SCR/302.BIN` |  |
| 1752929 | 5640 | `/SCR/303.BIN` |  |
| 1752932 | 5569 | `/SCR/304.BIN` |  |
| 1752935 | 5605 | `/SCR/305.BIN` |  |
| 1752938 | 5655 | `/SCR/306.BIN` |  |
| 1752941 | 6135 | `/SCR/307.BIN` |  |
| 1752944 | 6127 | `/SCR/308.BIN` |  |
| 1752947 | 5669 | `/SCR/309.BIN` |  |
| 1752950 | 5753 | `/SCR/310.BIN` |  |
| 1752953 | 6309 | `/SCR/311.BIN` |  |
| 1752957 | 5187 | `/SCR/312.BIN` |  |
| 1752960 | 5219 | `/SCR/313.BIN` |  |
| 1752963 | 5189 | `/SCR/314.BIN` |  |
| 1752966 | 5243 | `/SCR/315.BIN` |  |
| 1752969 | 5715 | `/SCR/316.BIN` |  |
| 1752972 | 5087 | `/SCR/317.BIN` |  |
| 1752975 | 5765 | `/SCR/318.BIN` |  |
| 1752978 | 5269 | `/SCR/319.BIN` |  |
| 1752981 | 6495 | `/SCR/320.BIN` |  |
| 1752985 | 5171 | `/SCR/321.BIN` |  |
| 1752988 | 5759 | `/SCR/322.BIN` |  |
| 1752991 | 5193 | `/SCR/323.BIN` |  |
| 1752994 | 5611 | `/SCR/324.BIN` |  |
| 1752997 | 5231 | `/SCR/325.BIN` |  |
| 1753000 | 5179 | `/SCR/326.BIN` |  |
| 1753003 | 5213 | `/SCR/327.BIN` |  |
| 1753006 | 5103 | `/SCR/328.BIN` |  |
| 1753009 | 5243 | `/SCR/329.BIN` |  |
| 1753012 | 5143 | `/SCR/330.BIN` |  |
| 1753015 | 5699 | `/SCR/331.BIN` |  |
| 1753018 | 5321 | `/SCR/332.BIN` |  |
| 1753021 | 5771 | `/SCR/333.BIN` |  |
| 1753024 | 5599 | `/SCR/334.BIN` |  |
| 1753027 | 5187 | `/SCR/335.BIN` |  |
| 1753030 | 5303 | `/SCR/336.BIN` |  |
| 1753033 | 5171 | `/SCR/337.BIN` |  |
| 1753036 | 5091 | `/SCR/338.BIN` |  |
| 1753039 | 5273 | `/SCR/339.BIN` |  |
| 1753042 | 5721 | `/SCR/340.BIN` |  |
| 1753045 | 5303 | `/SCR/341.BIN` |  |
| 1753048 | 5769 | `/SCR/342.BIN` |  |
| 1753051 | 90592 | `/BATTLE/ACC00.GSL` |  |
| 1753096 | 24864 | `/BATTLE/ARROW.GSL` |  |
| 1753109 | 63933728 | `/BATTLE/BFC.BIN` |  |
| 1784327 | 63909152 | `/BATTLE/BMT.BIN` |  |
| 1815533 | 63606048 | `/BATTLE/BSP.BIN` |  |
| 1846591 | 131583376 | `/BATTLE/BST.BIN` |  |
| 1910841 | 200576 | `/BATTLE/BT_LIST.BIN` |  |
| 1910939 | 62458144 | `/BATTLE/BWIN.BIN` |  |
| 1941437 | 74024 | `/BATTLE/CLUT.GSL` |  |
| 1941474 | 66848 | `/BATTLE/COUNT.GSL` |  |
| 1941507 | 20352 | `/BATTLE/DAY.GSL` |  |
| 1941517 | 22032 | `/BATTLE/DAY01.GSL` |  |
| 1941528 | 22032 | `/BATTLE/DAY02.GSL` |  |
| 1941539 | 22032 | `/BATTLE/DAY03.GSL` |  |
| 1941550 | 22032 | `/BATTLE/DAY04.GSL` |  |
| 1941561 | 22032 | `/BATTLE/DAY05.GSL` |  |
| 1941572 | 22032 | `/BATTLE/DAY06.GSL` |  |
| 1941583 | 22032 | `/BATTLE/DAY07.GSL` |  |
| 1941594 | 22032 | `/BATTLE/DAY08.GSL` |  |
| 1941605 | 22032 | `/BATTLE/DAY09.GSL` |  |
| 1941616 | 22032 | `/BATTLE/DAY10.GSL` |  |
| 1941627 | 22032 | `/BATTLE/DAY11.GSL` |  |
| 1941638 | 22032 | `/BATTLE/DAY12.GSL` |  |
| 1941649 | 22032 | `/BATTLE/DAY13.GSL` |  |
| 1941660 | 22032 | `/BATTLE/DAY14.GSL` |  |
| 1941671 | 22032 | `/BATTLE/DAY15.GSL` |  |
| 1941682 | 22032 | `/BATTLE/DAY16.GSL` |  |
| 1941693 | 58912 | `/BATTLE/MAN00.GSL` |  |
| 1941722 | 90592 | `/BATTLE/MAN01.GSL` |  |
| 1941767 | 90592 | `/BATTLE/MAN02.GSL` |  |
| 1941812 | 319184 | `/BATTLE/MATCH.GSL` |  |
| 1941968 | 144928 | `/BATTLE/MMAKE.GSL` |  |
| 1942039 | 166688 | `/BATTLE/MMAKE2.GSL` |  |
| 1942121 | 166688 | `/BATTLE/MMAKE4.GSL` |  |
| 1942203 | 3632 | `/BATTLE/MMAKEC.BIN` |  |
| 1942205 | 66848 | `/BATTLE/MM_ALL01.GSL` |  |
| 1942238 | 88928 | `/BATTLE/MM_LEA00.GSL` |  |
| 1942282 | 88640 | `/BATTLE/MM_LEA03.GSL` |  |
| 1942326 | 88928 | `/BATTLE/MM_LEA06.GSL` |  |
| 1942370 | 81184 | `/BATTLE/MM_PT0.GSL` |  |
| 1942410 | 65312 | `/BATTLE/MM_PT1.GSL` |  |
| 1942442 | 77088 | `/BATTLE/MM_TBG00.GSL` |  |
| 1942480 | 77088 | `/BATTLE/MM_TBG01.GSL` |  |
| 1942518 | 77088 | `/BATTLE/MM_TBG02.GSL` |  |
| 1942556 | 165152 | `/BATTLE/READY.GSL` |  |
| 1942637 | 129312 | `/BATTLE/TL01.GSL` |  |
| 1942701 | 34080 | `/BATTLE/VS.GSL` |  |
| 1942718 | 95338224 | `/BATTLE/WAZA.BIN` |  |
| 1989270 | 103712 | `/BATTLE/WIN00.GSL` |  |
| 1989321 | 103712 | `/BATTLE/WIN01.GSL` |  |
| 1989372 | 103712 | `/BATTLE/WIN02.GSL` |  |

## Executable and memory
*From the code.* `SLPM_550.56` is an ELF with one PT_LOAD: file 0x1000 → 0x200000, 0x39e600
bytes, memory size 0xea8094 (.bss ends at 0x10a8094). Sections: .text 0x200000-0x3768f8, .data
0x376900, .rodata 0x410680, .sdata 0x598c00, .sbss/.bss 0x59e600-0x10a8094. `$gp` = 0x5a0bf0.
Entry 0x30e410 (crt0): SetupThread(gp, stack 0x1f80000, size 0x80000), then SetupHeap(_end =
0x10a8094, -1) at 0x30e5d8 - the heap runs from the end of .bss up to the stack. Nothing in the
code addresses memory above .bss directly (checked: every `lui` 0x10b-0x1ff is a constant).
*From play-testing:* malloc doesn't use SetupHeap's value. It gets memory from `sbrk()` (0x3519f0),
which keeps its current break in the .data word 0x4027c4, initialised to _end (0x10a8094).

The English build appends a second PT_LOAD at 0x10a8100 for moved strings, and moves both
SetupHeap's argument and the sbrk break past it (tools/exetext.py). The first test build moved
only SetupHeap's argument. The game's first allocations then overwrote the moved strings, which
showed as blank boxes or rows of garbage glyphs.

The code uses R5900 128-bit saves (`sq`/`lq` sN, 0x20(sp)...) and EABI argument registers
a0-a3, t0-t3. capstone shows `sq`/`lq` as `.word` or odd MIPS32 mnemonics.

## Archives and compression
None found yet. Scripts and the font are plain files; `.GSL` files are raw GS upload packets (DMA
tags whose register writes - BITBLTBUF/TRXPOS/TRXREG - sit behind RAM-address references).

## Text

### How text is drawn (*from the code*)
Everything on screen goes through one font class, `pao::basic_Font` (vtable 0x4046d0):
- 0x20d750 `draw(this, x, y, p)`: a byte < 0x80 is drawn from glyph 0x1ed + code as a 12 px wide
  sprite and x += 11 (0x20: no sprite); a Shift-JIS pair is drawn 22 px wide, x += 22 (0x8140:
  x += 20; 0x849f is drawn as 0x815c). Bytes < 0x20 draw nothing.
- 0x20d720 `width(this, str)`: 11 px per byte.
- Two routines measure text themselves, at 11 px per byte (22 per Shift-JIS character):
  - 0x22f290 appends a line to a text block (vtable 0x404c80; buffer +0x1c, length +0x10, width
    +0x14, at most 0x7e bytes per line). The block centres each line on that width; the memory
    card notices use it.
  - 0x2b7998 returns the width of a string's first line.
- 0x20d880 draws up to N bytes or to a line break (typewriter), 0x20d970 a whole string,
  0x20da20 / 0x20dab0 the ▲ / ▼ cursor glyphs.
- 0x308e30 puts a glyph in the glyph cache (texture at 0x5dfb00) and returns its u, v; 0x308c98
  turns a code into a glyph number (bytes: + 0x1ed; Shift-JIS: JIS row/cell, rows above 15 shifted
  down by 0x316); 0x302cd0 draws a sprite (ctx, x, y, u, v, w, h - low 16 bits of each).

`/SYS/FONT.BIN`: 7018 glyphs of 22x22 at 4 bpp (242 bytes each, low nibble first), JIS order.
Pixel values 1-4 are the dark outline, 8-15 the white fill. The half-width set (glyphs 0x20e-
0x26b, codes 0x21-0x7e) is JIS-Roman (0x5c ¥, 0x7e overline), a condensed gothic left-aligned
in an 11 px grid.

The English build (tools/font.py) makes the half-width set proportional: glyphs moved to column
0, an advance table for 0x20-0x7f, draw()/width() rewritten (the table sits where the merged ▲/▼
functions were), and 0x81ad (unassigned) drawn as nothing with no advance. The two measuring
routines above use the same table.

### Event scripts `/SCR/*.BIN` (*from the code*, round trip verified on all 242)
A table of u32 offsets (segment starts, then the file size, then 0; padded to 16 bytes), then
segments - one scene each - of CRLF text ending in NUL, padded to 16 (the last one isn't).
The engine interprets the text (loader 0x200b60: buffer 0x59ea40, at most 0x40000 bytes, else
"Script Size is too large!!").

Files: 001-079 one per wrestler, 101-179 the same wrestler's other persona (same scenes, other
names), 201-242 foreign wrestlers, 301-342 their other persona. Each wrestler has ~108 scenes
(scouting, tryouts, contract talks, training, retirement ...).

Tokenizer 0x227698 (token end 0x30a248): skips spaces, tabs and line breaks before a token; a
token ends at space, tab, LF, `\`, `,`, `//`, or after `)`; `"..."` and `【...】` are read
whole; two-byte characters are stepped over. Classifier 0x229fc0 switches on the first byte
(jump table 0x475230): command words (`if go cg bg se bgm th dd da item ...`, names in .sdata
0x599800), `\c(...)` speaker, `%` (e.g. `%chr`) a message; any other byte < 0x80 a label; a
Shift-JIS byte starts a message. Message builder 0x22b6f0: tokens are appended with nothing
between them, `\n` becomes LF, `\w` waits, `\b` ends the message.

Consequences for English (tools/scr.py): spaces, commas and double quotes are stored as `_`,
`` ` `` and `^` (drawn as space, comma, quote); a line starting with ASCII is prefixed with the
zero-width 0x81ad.

### Message window (*from the code*)
0x231a98 (called from 0x232dec) draws 3 lines at y 0x15e/+0x18/+0x30, x 0xac (or 0x7c), each at
most 0x28 bytes and up to a line break; the speaker name at (window x + 0x20, 0x136) via
0x20d970. Typewriter progress 0x8c(window) grows by 1-2 per frame until the whole message has been
drawn; "show all" sets it to 0x96 (0x232ec0, 0x232f34). The English build raises the line cap to
0x60 and "show all" to 0x7fff (tools/font.py MESSAGE_BOX).

### The executable's text
- Strings reached through pointer tables or lui/addiu pairs: `translation/text/exe.csv`
  (tools/exetext.py) - about 4,600, of which 56 can only be changed in place.
- Roster 0x510114: 243 records of 0x848 bytes; +0 name, +0x40 ring name, +0x80 short name,
  +0x7f4 title, 0x40 bytes each (records.py `roster`). 0-78 main roster, 79-157 the other
  personas, 158-241 foreign wrestlers, 242 the secretary.
- Moves 0x4ff988: 223 records of 264 bytes; +0 name (0x40), +0x40 id `Wnnn` (records.py `moves`).
- Not yet mapped: venues (0x4e0330-0x4ea550, ~1,000 names), staff credits (0x466d4c, 124-byte
  records), region/prefecture names in 8-byte slots in .sdata (0x598f40-0x59e310), more move
  tables.

### Other files
`/SYS/BELT.DAT`, `BEL.BIN`, `OPTION.BIN`, `SLFILE.BIN`, `GALETC.BIN`, `BG.BIN`, `GM_*.BIN`: no text
(their Shift-JIS hits are image data). Menu and screen titles are images in the `.GSL` files.

## Images
*From the code / verified by round trip.* `.GSL` (265 files, 572 pictures): DMA chains of GIF
packets. Each upload: A+D writes of BITBLTBUF/TRXPOS/TRXREG/TRXDIR (junk in the upper bits of the
register field), then an IMAGE GIF tag with linear pixels. Pictures are PSMT8 (0x13) or PSMT4
(0x14), each followed by its CLUT (16x16 PSMCT32; 8-bit CLUTs in CSM1 order, alpha 0x80 =
opaque). tools/gfx.py exports and imports them (indexed PNG in the game's palette); re-importing
every unchanged picture gives identical files. 79 pictures hold Japanese text:
translation/graphics.csv. Contact sheets: review/gsl_contact_*.png.

## Open questions
- Speaker name box width; whether 【】 are drawn.
- Text drawn with widths computed as bytes x 11 outside width() (centred menus) - check in game.
- Which `.GSL` images hold text, and their pixel format.
- Whether anything compares roster names (save data copies them at a new game?).
