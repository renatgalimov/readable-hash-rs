# Multilingual phrase tables: offensiveness vs. readability

251 tables built with the frozen v5 compiler and rules; each encodes the same 20,000 random 64-bit values. Lower is better in every column except the word columns. Ranked by a combined score (offensive words first, then hard-to-say words, then length).

Baseline, today's English tables: 27.29 chars, 0.365% English-list hits, 0.22% severe, 0.605% major lists.

| # | tables | chars | 3+ cons. % | EN words % | own words % | EN list % | EN severe % | own list % | major lists % | any list % | inside 5+ % | relaxed rows | sample |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | Zulu + Basque (zu+eu-block) | 27.89 | 5.318 | 0.721 | 21.078 | 0.0 | 0.0 | 0.0 | 0.0 | 0.855 | 1.22 | 1 | egilayo ibean pero epitokwa |
| 2 | Basque + Finnish (eu+fi-block) | 27.36 | 3.455 | 0.914 | 19.623 | 0.0 | 0.0 | 0.0 | 0.0 | 0.87 | 1.47 | 2 | oneren buek unetan krosizten |
| 3 | Esperanto (eo-block) | 26.88 | 6.684 | 1.394 | 25.496 | 0.0 | 0.005 | 0.0 | 0.0 | 1.18 | 1.24 | 2 | plidge blia eteco acalifto |
| 4 | Zulu + Xhosa + Ganda + Shona (zu+xh+lg+sn-block) | 27.36 | 4.313 | 0.687 | 25.722 | 0.0 | 0.0 | 0.0 | 0.0 | 0.92 | 1.535 | 4 | leembwa icanga apere edweyako |
| 5 | Basque (eu-block) | 28.49 | 4.692 | 0.655 | 18.116 | 0.0 | 0.0 | 0.0 | 0.0 | 0.42 | 1.435 | 0 | aierarekin tiean fuek klilitazioa |
| 6 | Turkish + Zulu (tr+zu-block) | 27.38 | 5.74 | 0.742 | 21.831 | 0.0 | 0.0 | 0.0 | 0.0 | 0.82 | 1.715 | 2 | cakteki suma wole cottitir |
| 7 | Kabyle (kab-block) | 26.35 | 9.999 | 0.628 | 25.39 | 0.0 | 0.0 | 0.0 | 0.0 | 0.52 | 0.695 | 40 | feread saren sisi sbewwugun |
| 8 | Zulu + Xhosa (zu+xh-block) | 28.64 | 6.878 | 0.365 | 18.014 | 0.0 | 0.0 | 0.0 | 0.0 | 0.39 | 1.33 | 9 | ikwila efeli mbatha opotyika |
| 9 | Ganda (lg-block) | 29.01 | 4.28 | 0.869 | 21.522 | 0.0 | 0.0 | 0.0 | 0.0 | 0.41 | 1.11 | 24 | gyongamu oyaba tito ffetuumira |
| 10 | Zulu (zu-block) | 28.76 | 6.686 | 0.498 | 19.022 | 0.0 | 0.0 | 0.0 | 0.0 | 0.535 | 1.26 | 12 | iyakuwo iqiwe moto avuyolele |
| 11 | Greek (el-block) | 27.89 | 10.602 | 1.365 | 23.357 | 0.0 | 0.0 | 0.0 | 0.0 | 0.52 | 1.33 | 12 | vrykto egkta myiko omvalesei |
| 12 | Finnish (fi-block) | 28.21 | 3.157 | 1.404 | 20.521 | 0.0 | 0.005 | 0.0 | 0.0 | 0.905 | 1.655 | 33 | repetti ehasta shea uulipata |
| 13 | Turkish (tr-block) | 27.3 | 5.942 | 0.883 | 18.463 | 0.0 | 0.0 | 0.0 | 0.0 | 0.89 | 1.67 | 42 | fiserim kruk rodin prazaslari |
| 14 | English (en-v5-block) | 27.31 | 15.738 | 21.129 | 21.129 | 0.0 | 0.015 | 0.0 | 0.0 | 0.95 | 1.495 | 1 | cumman quion nings whinfened |
| 15 | Latin (la-block) | 27.5 | 6.798 | 4.175 | 23.028 | 0.0 | 0.005 | 0.0 | 0.0 | 0.685 | 1.72 | 47 | orbare hita euta guelagni |
| 16 | Kabyle (kab) | 26.3 | 8.541 | 0.651 | 25.628 | 0.04 | 0.005 | 0.135 | 0.165 | 0.83 | 1.155 | 38 | feread saren sisi sbewwugel |
| 17 | Xhosa (xh-block) | 28.93 | 7.204 | 0.313 | 12.745 | 0.0 | 0.0 | 0.0 | 0.0 | 0.44 | 1.815 | 60 | nibonga ecelwe oyala ucaphumelekile |
| 18 | Shona (sn-block) | 28.96 | 4.262 | 0.887 | 21.579 | 0.0 | 0.0 | 0.0 | 0.0 | 0.49 | 3.68 | 28 | apopia soura dunhu fupetuma |
| 19 | Zulu + Xhosa + Ganda + Shona (zu+xh+lg+sn) | 27.37 | 4.122 | 0.703 | 25.85 | 0.05 | 0.065 | 0.155 | 0.26 | 1.315 | 3.16 | 4 | lenywe icanga apere edweyako |
| 20 | Ganda (lg) | 28.98 | 3.96 | 0.84 | 21.691 | 0.0 | 0.04 | 0.0 | 0.395 | 0.805 | 2.035 | 24 | gyongamu oyaba tito ffetisiddwa |
| 21 | Berber languages (ber) | 26.34 | 10.14 | 0.514 | 23.805 | 0.005 | 0.02 | 0.0 | 0.43 | 0.98 | 1.21 | 63 | yusmum maet ayut nunejjren |
| 22 | Lower Sorbian (dsb) | 27.07 | 13.56 | 0.204 | 15.97 | 0.005 | 0.05 | 0.0 | 0.345 | 1.26 | 1.4 | 42 | degoty mrma zweje bydluponoma |
| 23 | Ancient Greek (grc) | 27.37 | 7.186 | 1.222 | 15.375 | 0.1 | 0.01 | 0.0 | 0.42 | 1.025 | 1.935 | 55 | megetas oxta iloy avaytrias |
| 24 | Zulu + Xhosa (zu+xh) | 28.62 | 6.838 | 0.361 | 18.17 | 0.0 | 0.035 | 0.13 | 0.535 | 1.055 | 2.77 | 9 | ikwila efeli mbatha opotyika |
| 25 | Divehi (dv) | 30.3 | 5.877 | 0.517 | 15.203 | 0.005 | 0.01 | 0.0 | 0.18 | 0.405 | 2.85 | 49 | rovugai pokamash ivakash joathuvumakee |
| 26 | Basque (eu) | 28.48 | 3.98 | 0.694 | 18.589 | 0.055 | 0.05 | 0.07 | 0.665 | 1.06 | 2.69 | 0 | aierarekin tiean fuek klilitazioa |
| 27 | Zulu (zu) | 28.73 | 6.406 | 0.525 | 19.254 | 0.0 | 0.02 | 0.205 | 0.6 | 1.34 | 2.76 | 11 | iyakuwo iqiwe moso avuyolele |
| 28 | Tajik (tg) | 26.54 | 10.061 | 0.4 | 21.211 | 0.0 | 0.045 | 0.0 | 0.79 | 1.645 | 1.69 | 22 | deletro ilni onash reaniloro |
| 29 | Basque + Finnish (eu+fi) | 27.33 | 2.796 | 0.961 | 20.202 | 0.01 | 0.045 | 0.095 | 0.78 | 1.8 | 2.94 | 1 | oneren buek unetan krosiztu |
| 30 | Zulu (zu-noen) | 28.82 | 6.135 | 0.292 | 19.066 | 0.0 | 0.005 | 0.075 | 0.585 | 1.11 | 3.075 | 14 | iyathaka iqiswa adeni ivemibalo |
| 31 | Basque (eu-noen) | 28.52 | 3.78 | 0.208 | 17.359 | 0.075 | 0.045 | 0.1 | 0.7 | 1.115 | 2.6 | 29 | suhiei idera klek igronion |
| 32 | Afar (aa) | 30.63 | 0.786 | 0.186 | 7.552 | 0.005 | 0.01 | 0.0 | 0.22 | 0.735 | 2.925 | 88 | yigutton eyaanah uytoonuh leiyitelitoh |
| 33 | Georgian (ka) | 27.32 | 25.032 | 0.425 | 18.637 | 0.085 | 0.1 | 0.0 | 0.555 | 1.52 | 1.585 | 13 | soprara ures zars kuskhebia |
| 34 | Upper Sorbian (hsb) | 26.3 | 16.12 | 0.19 | 23.321 | 0.005 | 0.07 | 0.0 | 0.67 | 1.87 | 1.985 | 28 | pjorku ziej nuci awcistiku |
| 35 | Gulf Arabic (afb) | 27.32 | 34.992 | 0.059 | 19.779 | 0.05 | 0.05 | 0.0 | 0.15 | 0.35 | 0.935 | 100 | ndshalaw ilaa sdis yjakthyh |
| 36 | Esperanto (eo) | 26.86 | 6.048 | 1.396 | 26.185 | 0.0 | 0.02 | 0.16 | 1.055 | 2.47 | 2.43 | 1 | plidigas blia eteco acalbolo |
| 37 | Egyptian Arabic (arz) | 25.44 | 41.157 | 0.281 | 29.4 | 0.175 | 0.09 | 0.0 | 0.27 | 1.0 | 1.19 | 19 | dywsht patiy tury mlnicino |
| 38 | Esperanto + Latin (eo+la) | 26.74 | 5.638 | 3.655 | 26.154 | 0.065 | 0.06 | 0.205 | 0.93 | 2.155 | 2.78 | 1 | lettan emia huaj jugoedojn |
| 39 | Turkmen (tk) | 28.25 | 5.209 | 1.103 | 7.566 | 0.06 | 0.095 | 0.0 | 0.755 | 1.52 | 1.905 | 64 | pubayar eren fily nistlunde |
| 40 | Xhosa (xh) | 28.91 | 7.14 | 0.335 | 12.854 | 0.055 | 0.1 | 0.0 | 0.515 | 0.955 | 2.6 | 59 | nifiza ecelwe oyala ucaphumelekile |
| 41 | Somali (so) | 27.39 | 2.702 | 0.604 | 16.617 | 0.07 | 0.005 | 0.0 | 1.25 | 1.855 | 1.485 | 51 | ogtidii yinka olin losimadan |
| 42 | Kazakh (kk) | 28.48 | 12.09 | 0.723 | 16.731 | 0.005 | 0.02 | 0.0 | 0.76 | 1.2 | 2.225 | 49 | iskata plarda iegha opulandy |
| 43 | Sundanese (su) | 26.76 | 6.89 | 1.349 | 29.042 | 0.075 | 0.06 | 0.0 | 0.9 | 2.665 | 3.1 | 1 | nyetkan agik kladi optempel |
| 44 | Turkish + Zulu (tr+zu) | 27.38 | 4.695 | 0.8 | 22.227 | 0.0 | 0.03 | 0.075 | 1.02 | 1.84 | 3.085 | 1 | caktuk suisa wole cottulala |
| 45 | Slovak (sk) | 25.76 | 10.486 | 0.668 | 27.831 | 0.175 | 0.075 | 0.26 | 0.86 | 2.11 | 2.78 | 2 | provity runa elle aketskami |
| 46 | Central Kurdish (ckb) | 26.61 | 47.966 | 0.152 | 29.679 | 0.165 | 0.04 | 0.0 | 0.29 | 0.515 | 0.575 | 54 | yrngry snky dkey hteshkhty |
| 47 | Malayalam (ml) | 28.53 | 42.45 | 0.487 | 26.031 | 0.065 | 0.015 | 0.09 | 0.465 | 1.105 | 1.48 | 1 | pilutum otman vntan kyricconin |
| 48 | Nande (nnb) | 28.97 | 2.803 | 0.775 | 18.081 | 0.0 | 0.01 | 0.0 | 0.455 | 1.095 | 1.87 | 173 | mbubwa henda ubaha tobirimo |
| 49 | Lithuanian (lt) | 26.4 | 5.373 | 0.632 | 24.499 | 0.01 | 0.055 | 0.02 | 1.1 | 2.23 | 2.045 | 30 | slingu dvija hola fokyleti |
| 50 | Burmese (my) | 27.68 | 52.629 | 0.194 | 15.179 | 0.08 | 0.01 | 0.16 | 0.145 | 1.18 | 0.92 | 63 | dakhaitiuk klam haiu yeaksurhnk |
| 51 | Breton (br) | 26.12 | 6.822 | 1.578 | 26.267 | 0.25 | 0.105 | 0.0 | 1.01 | 1.965 | 2.41 | 7 | drinek orad iman avjerissa |
| 52 | Greek (el) | 27.85 | 9.674 | 1.472 | 23.841 | 0.005 | 0.085 | 0.09 | 0.79 | 1.41 | 3.135 | 11 | vrykto egkta myiko omvalesei |
| 53 | Korean (ko) | 29.27 | 10.096 | 0.252 | 24.541 | 0.0 | 0.015 | 0.22 | 0.8 | 1.585 | 1.545 | 85 | tobeleul ihog tiui elguineyo |
| 54 | English (en-v5) | 27.29 | 13.629 | 21.897 | 21.897 | 0.365 | 0.22 | 0.365 | 0.605 | 1.425 | 2.715 | 0 | cumman quion nings whinthly |
| 55 | Mongolian (mn) | 27.65 | 20.267 | 0.535 | 20.484 | 0.055 | 0.11 | 0.075 | 0.48 | 0.845 | 1.72 | 86 | aglogt aten kiyg ragdasyn |
| 56 | Welsh (cy) | 26.6 | 17.221 | 1.579 | 22.24 | 0.405 | 0.26 | 0.345 | 0.755 | 1.68 | 1.46 | 3 | bwlyau byne lyra achimiaeth |
| 57 | Old English (ang) | 27.77 | 16.433 | 1.743 | 22.696 | 0.14 | 0.115 | 0.0 | 1.02 | 1.6 | 1.455 | 13 | bollienne roed cust nyolbaerre |
| 58 | Nepali (ne) | 27.44 | 41.245 | 0.404 | 33.837 | 0.055 | 0.04 | 0.0 | 0.535 | 0.985 | 1.75 | 3 | hundai ktabat turma mekholle |
| 59 | Silesian (szl) | 28.45 | 7.546 | 0.799 | 5.344 | 0.265 | 0.13 | 0.0 | 0.86 | 1.65 | 2.6 | 17 | loloki jerum wjus verthracella |
| 60 | Luxembourgish (lb) | 28.4 | 21.318 | 2.87 | 22.969 | 0.08 | 0.09 | 0.0 | 0.41 | 1.44 | 3.64 | 4 | horaaft nang vott abrutsen |
| 61 | Mingrelian (xmf) | 28.0 | 12.587 | 0.634 | 8.493 | 0.175 | 0.045 | 0.0 | 0.505 | 1.295 | 2.785 | 100 | limbepish imili usli ughanonaluri |
| 62 | Persian (fa) | 26.36 | 75.249 | 0.001 | 37.361 | 0.0 | 0.0 | 0.27 | 0.075 | 0.43 | 0.13 | 24 | thisym jdyr rzty hldhychnd |
| 63 | Standard Latvian (lvs) | 26.52 | 9.825 | 1.061 | 28.011 | 0.075 | 0.055 | 0.0 | 1.16 | 2.95 | 2.0 | 20 | akrejot gues zoda iljoncis |
| 64 | Gothic (got) | 30.12 | 11.461 | 0.921 | 8.198 | 0.08 | 0.01 | 0.0 | 0.425 | 1.25 | 2.955 | 77 | kuridedum bonds itam asnomeai |
| 65 | Kyrgyz (ky) | 26.75 | 11.209 | 0.868 | 14.308 | 0.045 | 0.08 | 0.0 | 0.875 | 1.51 | 2.32 | 46 | oldonun acka brdan imolyasyna |
| 66 | Sinhala (si) | 25.38 | 31.215 | 0.448 | 31.818 | 0.28 | 0.07 | 0.0 | 0.94 | 2.055 | 1.015 | 3 | mhtenm roks pnuvn abhaudagen |
| 67 | Halh Mongolian (khk) | 28.12 | 25.723 | 0.124 | 13.242 | 0.0 | 0.005 | 0.0 | 0.26 | 0.515 | 1.5 | 166 | tiylliyg kalyg gyiyg pramtalzh |
| 68 | Yakut (sah) | 31.26 | 9.788 | 0.465 | 8.71 | 0.0 | 0.025 | 0.0 | 0.225 | 0.38 | 3.65 | 59 | praargytyna ubon omtyttan idaydyttan |
| 69 | Gilaki (glk) | 26.39 | 76.319 | 0.003 | 37.493 | 0.0 | 0.0 | 0.0 | 0.0 | 0.46 | 0.17 | 37 | knnwyny glny whdy tmypdrmwn |
| 70 | Northern Sami (se) | 30.77 | 15.297 | 0.473 | 8.562 | 0.11 | 0.005 | 0.0 | 0.395 | 1.195 | 2.12 | 101 | liarit urit ocin pananasin |
| 71 | Russian (ru) | 26.74 | 15.68 | 0.337 | 24.861 | 0.07 | 0.08 | 0.23 | 0.87 | 2.155 | 2.805 | 12 | rassprana geku ogli frolnikom |
| 72 | Faroese (fo) | 28.11 | 15.428 | 1.236 | 21.806 | 0.085 | 0.04 | 0.0 | 0.93 | 1.655 | 3.075 | 10 | elegni slingin endurinum folkabogast |
| 73 | Slovenian (sl) | 25.89 | 14.102 | 0.759 | 29.348 | 0.07 | 0.005 | 0.28 | 1.39 | 3.5 | 1.91 | 0 | capoli hine faci zrirovanju |
| 74 | Norwegian Bokmål (nb) | 28.14 | 17.137 | 2.481 | 22.783 | 0.135 | 0.1 | 0.0 | 0.735 | 2.2 | 3.235 | 11 | ekskosen dyket etteres sunkuliene |
| 75 | Hungarian (hu) | 26.67 | 8.082 | 0.968 | 25.024 | 0.19 | 0.205 | 0.14 | 0.845 | 2.165 | 2.545 | 33 | isgytak cabol gesa izitkeztem |
| 76 | Latin (la) | 27.43 | 5.344 | 4.248 | 23.638 | 0.155 | 0.065 | 0.05 | 0.875 | 1.56 | 3.565 | 46 | orbare hita euta guelagni |
| 77 | Arabic (ar) | 25.63 | 76.989 | 0.0 | 38.678 | 0.06 | 0.0 | 0.09 | 0.235 | 0.45 | 0.2 | 15 | tfhrytn slys sbhy wrakrwyh |
| 78 | Icelandic (is) | 27.04 | 19.563 | 1.207 | 26.945 | 0.01 | 0.045 | 0.18 | 1.105 | 2.36 | 2.225 | 9 | tiundid mylegt lykur bjingkokur |
| 79 | Papiamento (pap) | 28.38 | 5.36 | 1.805 | 14.352 | 0.2 | 0.1 | 0.0 | 0.925 | 2.035 | 3.645 | 14 | kabolo shado wind evenschamento |
| 80 | Ndonga (ng) | 28.48 | 4.398 | 0.578 | 16.806 | 0.005 | 0.065 | 0.0 | 0.74 | 1.47 | 2.96 | 102 | mbiiva leilo unya vuopeleka |
| 81 | Northern Kurdish (kmr) | 26.62 | 6.484 | 0.749 | 19.542 | 0.18 | 0.085 | 0.0 | 1.03 | 1.66 | 2.57 | 58 | ajorte penin tina ipokbeno |
| 82 | Waray (war) | 27.91 | 6.965 | 3.514 | 18.226 | 0.155 | 0.02 | 0.0 | 1.01 | 2.325 | 4.31 | 0 | cibosus frium ricta ecphopoma |
| 83 | Armenian (hy) | 28.58 | 23.079 | 0.423 | 19.99 | 0.005 | 0.245 | 0.16 | 0.37 | 1.225 | 2.455 | 38 | ograna nvners tnin zikalnern |
| 84 | Sanskrit (sa) | 27.46 | 41.645 | 0.143 | 29.669 | 0.065 | 0.095 | 0.0 | 0.66 | 1.37 | 1.635 | 3 | utkhaih pinam rtesu plavijne |
| 85 | Finnish (fi-noen) | 28.21 | 1.969 | 0.426 | 20.709 | 0.145 | 0.105 | 0.095 | 0.845 | 1.895 | 4.18 | 29 | etanille rykaa lyla darkeihin |
| 86 | Uzbek (uz) | 28.79 | 11.425 | 0.703 | 12.764 | 0.0 | 0.025 | 0.07 | 1.065 | 2.42 | 3.1 | 10 | stevali kradi qiyga illoqladi |
| 87 | Old Norse (non) | 28.32 | 20.662 | 0.669 | 22.478 | 0.05 | 0.03 | 0.0 | 0.67 | 1.16 | 2.77 | 70 | rossask knit efir ufrulgumk |
| 88 | Hebrew (he) | 27.39 | 77.143 | 0.001 | 33.834 | 0.0 | 0.0 | 0.0 | 0.0 | 0.165 | 0.105 | 75 | tthlykhh ftmym ndyr nfhysvkrym |
| 89 | Thai (th) | 27.99 | 33.41 | 0.816 | 16.814 | 0.125 | 0.015 | 0.19 | 0.745 | 2.07 | 2.345 | 29 | yiwkoy oldi fuely kehlwnmak |
| 90 | Kurdish (ku) | 26.61 | 55.59 | 0.098 | 22.333 | 0.0 | 0.03 | 0.0 | 0.28 | 0.615 | 0.82 | 84 | zewtne fhty jhne monmezrenn |
| 91 | Western Panjabi (pnb) | 25.86 | 79.079 | 0.025 | 38.433 | 0.005 | 0.005 | 0.0 | 0.075 | 0.71 | 0.165 | 52 | bdkhyri lbrty rhne rkntynsrn |
| 92 | Plateau Malagasy (plt) | 27.87 | 4.384 | 1.505 | 12.955 | 0.09 | 0.05 | 0.0 | 0.65 | 1.52 | 4.025 | 100 | kinsatra aolo ioany ervezela |
| 93 | Walloon (wa) | 27.38 | 11.966 | 2.353 | 16.275 | 0.065 | 0.075 | 0.0 | 0.66 | 1.47 | 2.69 | 118 | plumit dmike keute afrurite |
| 94 | Belarusian (be) | 27.82 | 19.619 | 0.259 | 17.185 | 0.0 | 0.07 | 0.18 | 0.855 | 2.075 | 2.775 | 40 | znutnym glala yuay tulushykh |
| 95 | Latvian (lv) | 26.26 | 9.57 | 0.661 | 26.827 | 0.185 | 0.095 | 0.175 | 1.27 | 3.215 | 2.215 | 26 | dresas tosu avas opdeklija |
| 96 | Tosk Albanian (als) | 26.65 | 12.271 | 1.51 | 26.621 | 0.095 | 0.125 | 0.0 | 1.205 | 2.935 | 2.325 | 9 | catite plore tina xhehtonte |
| 97 | Czech (cs) | 25.66 | 13.25 | 0.571 | 28.507 | 0.2 | 0.17 | 0.22 | 1.05 | 2.82 | 2.665 | 1 | nortie fail jinou altanedlo |
| 98 | Finnish (fi) | 28.14 | 2.223 | 1.441 | 21.013 | 0.195 | 0.21 | 0.025 | 0.8 | 1.73 | 3.81 | 30 | repetti ehasta sheen uulipaus |
| 99 | Chechen (ce) | 29.19 | 22.161 | 0.559 | 12.42 | 0.065 | 0.045 | 0.0 | 0.385 | 1.615 | 3.18 | 90 | bityovo fiakh spal myrekhka |
| 100 | Zulu + Basque (zu+eu) | 27.9 | 4.995 | 0.719 | 21.467 | 0.0 | 0.28 | 0.105 | 0.97 | 1.895 | 3.09 | 1 | egilayo ibean pero epitatha |
| 101 | Tamil (ta) | 27.82 | 45.315 | 0.324 | 24.784 | 0.055 | 0.01 | 0.0 | 0.31 | 0.83 | 2.71 | 59 | cmarttin opti kmlai pcirukmaiyai |
| 102 | Eastern Mari (mhr) | 28.1 | 21.292 | 0.419 | 9.871 | 0.0 | 0.035 | 0.0 | 0.6 | 1.52 | 1.935 | 148 | tirikyshte klylan acysh drosnyzhe |
| 103 | Ido (io) | 28.54 | 3.22 | 1.412 | 19.986 | 0.14 | 0.09 | 0.0 | 0.825 | 2.235 | 5.17 | 1 | sortigor toonte debanta ecocebeti |
| 104 | Assamese (as) | 27.11 | 34.694 | 0.419 | 28.363 | 0.145 | 0.08 | 0.0 | 0.89 | 2.06 | 2.065 | 5 | munibnr teti pdsmuh trapkhinere |
| 105 | North Azerbaijani (azj) | 27.55 | 5.383 | 0.939 | 14.848 | 0.16 | 0.075 | 0.0 | 1.235 | 2.345 | 3.73 | 3 | icliqdan birinin yiler iledxalar |
| 106 | Estonian (et) | 26.27 | 5.802 | 1.101 | 24.261 | 0.21 | 0.025 | 0.33 | 1.36 | 3.305 | 2.66 | 50 | stilgi cani cosa ehekuulas |
| 107 | Polish (pl) | 26.55 | 14.706 | 0.738 | 22.269 | 0.275 | 0.245 | 0.305 | 1.115 | 2.145 | 1.97 | 1 | lesnic wzony frow muespeda |
| 108 | Turkish (tr-noen) | 27.55 | 4.372 | 0.612 | 18.048 | 0.04 | 0.01 | 0.4 | 1.385 | 2.16 | 2.97 | 52 | fitiyi zame ailar oplumuze |
| 109 | Kalaallisut (kl) | 33.56 | 7.055 | 0.124 | 5.589 | 0.0 | 0.05 | 0.0 | 0.005 | 0.075 | 3.52 | 133 | uataatigut aitigut ogarput jotaanngap |
| 110 | Asturian (ast) | 26.85 | 3.888 | 2.579 | 28.268 | 0.21 | 0.185 | 0.0 | 1.14 | 2.06 | 3.115 | 31 | gundon axica luco ectelista |
| 111 | Mandarin Chinese (cmn) | 27.19 | 9.805 | 1.092 | 28.795 | 0.105 | 0.025 | 0.0 | 0.605 | 1.34 | 1.685 | 245 | zesushu brshi esan afuzimen |
| 112 | Tatar (tt) | 27.55 | 11.301 | 0.454 | 18.276 | 0.0 | 0.005 | 0.0 | 1.46 | 2.435 | 2.425 | 39 | agafen unyk gyda gekhnaga |
| 113 | Dimli (individual language) (diq) | 25.73 | 4.184 | 0.896 | 22.517 | 0.17 | 0.02 | 0.0 | 1.245 | 2.49 | 1.69 | 149 | sosnan ewti yide abivmana |
| 114 | Pashto (ps) | 26.59 | 77.62 | 0.019 | 29.309 | 0.0 | 0.0 | 0.0 | 0.17 | 0.585 | 0.135 | 85 | hykhwy nmedw nngy pkmenswr |
| 115 | Turkish (tr) | 27.22 | 5.206 | 1.015 | 18.84 | 0.15 | 0.08 | 0.385 | 1.325 | 2.31 | 3.04 | 39 | fiseyle kruk rodin prazziyor |
| 116 | Standard Estonian (ekk) | 26.6 | 5.765 | 1.266 | 20.08 | 0.265 | 0.09 | 0.0 | 1.175 | 3.055 | 3.465 | 44 | oprakud fuli boni imbulandi |
| 117 | Albanian (sq) | 25.97 | 12.955 | 1.339 | 29.035 | 0.18 | 0.14 | 0.09 | 1.41 | 3.28 | 2.13 | 8 | furrur noin ruka blaktojne |
| 118 | Coptic (cop) | 28.11 | 31.777 | 0.149 | 17.174 | 0.08 | 0.125 | 0.0 | 0.235 | 0.715 | 1.77 | 171 | abauji cbini ctji ademefbosh |
| 119 | Croatian (hr) | 26.14 | 10.995 | 1.061 | 32.912 | 0.08 | 0.015 | 0.465 | 1.705 | 3.32 | 2.19 | 8 | dadile ocio fona juljopao |
| 120 | Catalan (ca) | 27.1 | 5.802 | 2.841 | 25.384 | 0.02 | 0.055 | 0.195 | 1.265 | 2.535 | 3.35 | 51 | obitada aela xals xitinges |
| 121 | Japanese (ja) | 28.45 | 5.485 | 0.247 | 27.245 | 0.065 | 0.015 | 0.515 | 1.265 | 2.015 | 2.655 | 94 | okekuan yequ olng amagabiri |
| 122 | Northern Uzbek (uzn) | 29.73 | 17.525 | 0.61 | 17.014 | 0.105 | 0.15 | 0.0 | 0.715 | 1.56 | 3.61 | 11 | zamatni azhim vidan istkhlisligi |
| 123 | Iranian Persian (pes) | 26.55 | 77.476 | 0.003 | 32.589 | 0.0 | 0.0 | 0.0 | 0.12 | 0.57 | 0.24 | 102 | hsntyyy gywh lkhty nkwdyrsnd |
| 124 | Kinyarwanda (rw) | 28.36 | 2.772 | 0.679 | 19.836 | 0.01 | 0.05 | 0.0 | 0.86 | 1.15 | 4.2 | 101 | uwigaje coana uyera hekwifuka |
| 125 | Northern Sotho (nso) | 28.08 | 11.04 | 0.788 | 12.69 | 0.05 | 0.03 | 0.0 | 0.555 | 1.86 | 2.765 | 209 | ruroso rika yala lifobago |
| 126 | Swahili (individual language) (swh) | 27.55 | 6.755 | 0.894 | 15.746 | 0.17 | 0.135 | 0.0 | 1.165 | 2.395 | 2.96 | 59 | pojiua desi vyeza dipaliana |
| 127 | Mirandese (mwl) | 27.23 | 3.705 | 1.687 | 13.334 | 0.02 | 0.035 | 0.0 | 1.425 | 2.41 | 2.605 | 80 | cciplo josa usorun ajssites |
| 128 | Ukrainian (uk) | 26.96 | 15.313 | 0.339 | 24.912 | 0.005 | 0.055 | 0.175 | 1.225 | 2.56 | 3.455 | 13 | tonuiesh gluvati fanya fraieroga |
| 129 | Guarani (gn) | 27.91 | 1.832 | 0.936 | 10.147 | 0.19 | 0.065 | 0.0 | 1.13 | 1.9 | 1.87 | 175 | asonor vegua loava tiviativo |
| 130 | Irish (ga) | 28.02 | 19.167 | 1.163 | 22.478 | 0.36 | 0.11 | 0.0 | 1.31 | 2.815 | 1.65 | 47 | toiniu pich guiodh goltriuil |
| 131 | Western Frisian (fy) | 26.95 | 15.153 | 2.407 | 20.856 | 0.365 | 0.19 | 0.0 | 1.015 | 2.19 | 3.17 | 19 | huront inich nias chazebius |
| 132 | Rusyn (rue) | 26.7 | 14.815 | 0.193 | 7.995 | 0.0 | 0.045 | 0.0 | 0.605 | 1.48 | 3.15 | 165 | puarno kili zbky zrenalnu |
| 133 | Marathi (mr) | 27.5 | 36.467 | 0.394 | 32.299 | 0.245 | 0.155 | 0.115 | 1.13 | 2.385 | 1.225 | 6 | boises vsacya abhiat jogakhla |
| 134 | Minangkabau (min) | 27.25 | 5.597 | 1.861 | 12.403 | 0.05 | 0.1 | 0.0 | 1.255 | 1.95 | 3.675 | 37 | hidral erum agas kissenes |
| 135 | Bashkir (ba) | 27.46 | 10.216 | 0.41 | 16.568 | 0.0 | 0.03 | 0.0 | 1.695 | 2.35 | 2.41 | 21 | mersny amov ozde plikhirga |
| 136 | Buriat (bua) | 28.04 | 16.928 | 0.328 | 9.214 | 0.0 | 0.005 | 0.0 | 0.515 | 0.825 | 1.52 | 279 | ublgokho izzha xaye feubural |
| 137 | Urdu (ur) | 26.31 | 77.78 | 0.021 | 32.04 | 0.005 | 0.005 | 0.0 | 0.045 | 0.57 | 0.13 | 143 | bsrmyng tlhy gnyz tbhmykrdgy |
| 138 | Tswana (tn) | 28.43 | 11.752 | 1.342 | 16.647 | 0.18 | 0.12 | 0.0 | 0.69 | 1.83 | 2.46 | 171 | abaane hena ebeng eperamele |
| 139 | Javanese (jv) | 26.07 | 7.604 | 1.507 | 27.54 | 0.16 | 0.18 | 0.0 | 1.49 | 3.365 | 2.81 | 2 | wekasikan mruk jonge emliyana |
| 140 | Telugu (te) | 27.09 | 40.488 | 0.237 | 24.192 | 0.085 | 0.11 | 0.115 | 1.13 | 1.705 | 1.495 | 5 | dryiga vsmdi skym agdhiknu |
| 141 | Sardinian (sc) | 27.34 | 6.296 | 1.501 | 9.959 | 0.15 | 0.035 | 0.0 | 1.16 | 2.04 | 3.455 | 105 | loscare spicu eradu irotegus |
| 142 | Hindi (hi) | 25.75 | 33.372 | 0.117 | 37.666 | 0.085 | 0.015 | 0.225 | 1.56 | 3.07 | 1.37 | 7 | ktaviya rine trsa insiphom |
| 143 | Bosnian (bs) | 26.14 | 10.944 | 1.011 | 33.248 | 0.155 | 0.125 | 0.0 | 1.665 | 3.67 | 2.34 | 6 | libice zvila snaci alumljini |
| 144 | Anaang (anw) | 26.41 | 4.851 | 1.592 | 15.288 | 0.18 | 0.035 | 0.0 | 1.45 | 2.455 | 2.89 | 88 | rachon llsa eura sculgols |
| 145 | Newari (new) | 25.74 | 31.071 | 0.098 | 17.378 | 0.085 | 0.01 | 0.0 | 0.81 | 2.425 | 1.355 | 172 | moglay ptigu luim pehavnam |
| 146 | Serbian (sr) | 26.04 | 11.584 | 0.677 | 32.934 | 0.07 | 0.08 | 0.09 | 1.8 | 4.085 | 2.2 | 2 | biopci risa ekno chickadom |
| 147 | Low German (nds) | 27.12 | 24.391 | 2.572 | 22.532 | 0.195 | 0.21 | 0.0 | 0.725 | 1.915 | 3.945 | 15 | wormsch peung syten piesveres |
| 148 | Sicilian (scn) | 27.98 | 5.351 | 1.368 | 17.685 | 0.065 | 0.045 | 0.0 | 1.16 | 1.695 | 4.205 | 77 | ruscenza nzaru erettu toncrenti |
| 149 | Swahili (sw) | 27.26 | 5.886 | 1.055 | 25.183 | 0.28 | 0.225 | 0.0 | 1.455 | 2.3 | 2.925 | 8 | mmariri kwoa gemu uzapandisha |
| 150 | Filipino (fil) | 26.02 | 6.194 | 2.005 | 25.419 | 0.505 | 0.215 | 0.005 | 1.385 | 2.925 | 2.455 | 48 | ekisal rise quito wisiklap |
| 151 | Lombard (lmo) | 26.21 | 7.074 | 1.345 | 19.616 | 0.005 | 0.105 | 0.0 | 1.09 | 2.87 | 2.945 | 123 | roeusa vuss erita ostudott |
| 152 | Rundi (rn) | 28.13 | 3.274 | 0.669 | 16.297 | 0.14 | 0.1 | 0.0 | 0.76 | 1.27 | 4.39 | 135 | wibonze soana zuye famegikira |
| 153 | Malagasy (mg) | 28.78 | 5.948 | 1.072 | 9.7 | 0.005 | 0.035 | 0.0 | 0.63 | 1.145 | 4.72 | 141 | enanteny thony drona izatsetry |
| 154 | Gujarati (gu) | 26.8 | 36.691 | 0.754 | 37.091 | 0.055 | 0.07 | 0.0 | 1.37 | 2.235 | 1.655 | 1 | adasie likmam cese hilistmam |
| 155 | Azerbaijani (az) | 27.32 | 5.797 | 1.041 | 17.774 | 0.14 | 0.075 | 0.0 | 1.645 | 2.94 | 3.565 | 3 | fazilari ehik oxler nunlugler |
| 156 | Romansh (rm) | 26.89 | 13.271 | 1.574 | 19.157 | 0.09 | 0.105 | 0.0 | 1.175 | 2.15 | 3.185 | 67 | nursada tgica eser smogatica |
| 157 | Punjabi (pa) | 25.32 | 31.323 | 0.241 | 39.398 | 0.335 | 0.14 | 0.0 | 1.465 | 2.98 | 1.295 | 1 | gotain mmam ikle slirodam |
| 158 | Samogitian (sgs) | 27.0 | 6.721 | 1.094 | 8.034 | 0.15 | 0.045 | 0.0 | 1.375 | 2.22 | 1.855 | 158 | akalva ouna sreje eislanos |
| 159 | Ladino (lad) | 27.08 | 9.452 | 1.917 | 10.315 | 0.065 | 0.03 | 0.0 | 1.58 | 2.82 | 2.27 | 89 | kiatales bodo justo ofnsisas |
| 160 | Macedonian (mk) | 26.72 | 16.779 | 0.996 | 25.528 | 0.125 | 0.03 | 0.17 | 1.465 | 3.175 | 3.545 | 12 | vlarat gevme mrot gurgichar |
| 161 | Ingrian (izh) | 29.89 | 3.281 | 1.531 | 12.09 | 0.165 | 0.215 | 0.0 | 0.905 | 1.24 | 4.585 | 21 | doijat sanna tiinna simerren |
| 162 | Afrikaans (af) | 27.11 | 12.576 | 2.582 | 19.815 | 0.43 | 0.315 | 0.0 | 1.16 | 2.1 | 2.61 | 30 | poppot rias nues coolligte |
| 163 | Shona (sn) | 28.99 | 4.168 | 0.877 | 21.881 | 0.1 | 0.11 | 0.0 | 1.015 | 1.49 | 5.27 | 27 | apopia soura dunhu fuhungunda |
| 164 | Scots (sco) | 25.88 | 11.54 | 3.831 | 25.693 | 0.49 | 0.25 | 0.0 | 1.44 | 2.905 | 2.59 | 8 | nevard cily sked eslivity |
| 165 | Danish (da) | 26.76 | 14.613 | 3.132 | 27.285 | 0.39 | 0.32 | 0.41 | 1.11 | 3.075 | 3.25 | 1 | svekken kvos amon hjespejre |
| 166 | Southern Sotho (st) | 28.32 | 10.945 | 1.01 | 14.397 | 0.035 | 0.055 | 0.0 | 0.985 | 2.285 | 2.505 | 181 | sopolong weso yung rinyapela |
| 167 | Extremaduran (ext) | 26.98 | 4.3 | 1.383 | 10.803 | 0.09 | 0.085 | 0.0 | 1.415 | 2.545 | 2.49 | 125 | nereis avol obis erectorica |
| 168 | Portuguese (pt) | 26.82 | 4.755 | 2.717 | 29.78 | 0.26 | 0.185 | 0.595 | 1.595 | 2.815 | 3.44 | 1 | fendado flis kion rubrosta |
| 169 | Venetian (vec) | 28.42 | 5.1 | 2.354 | 19.776 | 0.12 | 0.13 | 0.0 | 1.325 | 2.365 | 4.775 | 0 | corolta emase glono smopolazione |
| 170 | Kituba (Congo) (mkw) | 26.58 | 19.219 | 1.094 | 24.423 | 0.175 | 0.015 | 0.0 | 1.335 | 3.075 | 4.375 | 4 | dantata jual ekite conizhal |
| 171 | Chuvash (cv) | 27.85 | 20.753 | 1.088 | 13.741 | 0.125 | 0.11 | 0.0 | 1.165 | 2.23 | 3.065 | 58 | urusar grakan adne zarmayan |
| 172 | Kannada (kn) | 28.93 | 53.074 | 0.268 | 25.785 | 0.265 | 0.22 | 0.15 | 0.605 | 1.545 | 1.875 | 1 | grenge ayiruv skhi yujivinlli |
| 173 | Sindhi (sd) | 25.95 | 75.192 | 0.017 | 31.199 | 0.0 | 0.0 | 0.0 | 0.125 | 0.615 | 0.19 | 188 | hnastn fljy tsmny bsithsyl |
| 174 | Kashubian (csb) | 26.99 | 23.737 | 0.448 | 9.3 | 0.085 | 0.02 | 0.0 | 1.13 | 2.22 | 1.68 | 169 | sowsza luja gdach umadzona |
| 175 | Bulgarian (bg) | 26.97 | 15.208 | 1.062 | 24.933 | 0.215 | 0.065 | 0.195 | 1.54 | 3.155 | 3.6 | 24 | yarker alni frost okularata |
| 176 | Amharic (am) | 27.28 | 32.766 | 0.331 | 19.0 | 0.14 | 0.175 | 0.0 | 0.755 | 1.19 | 1.79 | 141 | sbsona bhun hmwa sfnyitna |
| 177 | Romanian (ro) | 26.43 | 5.062 | 1.816 | 28.839 | 0.505 | 0.29 | 0.2 | 1.695 | 3.495 | 2.735 | 3 | freera esit herd ecascioasa |
| 178 | Limburgish (li) | 26.13 | 15.894 | 1.939 | 31.749 | 0.66 | 0.4 | 0.0 | 1.255 | 3.805 | 2.54 | 3 | camete chle ergs kwoadshuis |
| 179 | Uyghur (ug) | 29.55 | 42.163 | 0.359 | 9.299 | 0.0 | 0.0 | 0.0 | 0.655 | 0.975 | 1.92 | 145 | qyayadaka almen bhagh epqlansen |
| 180 | Classical Armenian (xcl) | 26.8 | 30.269 | 0.365 | 15.481 | 0.15 | 0.065 | 0.0 | 0.575 | 1.72 | 2.735 | 195 | hnkore gten acan vcgeshoy |
| 181 | Võro (vro) | 25.91 | 7.328 | 0.502 | 9.914 | 0.23 | 0.14 | 0.0 | 1.095 | 2.45 | 2.24 | 201 | eettuq feal slin oulgavva |
| 182 | Norwegian Nynorsk (nn) | 26.95 | 16.873 | 2.787 | 26.843 | 0.325 | 0.17 | 0.0 | 1.595 | 3.5 | 3.03 | 2 | gulfane gjeande fjellne hjaffaret |
| 183 | Tuvinian (tyv) | 32.84 | 28.289 | 0.353 | 5.052 | 0.0 | 0.005 | 0.0 | 0.42 | 0.635 | 2.36 | 159 | yrdirde usary niardan vediptarga |
| 184 | Piedmontese (pms) | 27.0 | 7.113 | 2.365 | 14.842 | 0.12 | 0.205 | 0.0 | 1.09 | 2.575 | 3.385 | 121 | gongela juich afal emodesca |
| 185 | Bangla (bn) | 25.99 | 29.337 | 1.149 | 36.436 | 0.515 | 0.25 | 0.0 | 1.38 | 2.82 | 2.11 | 1 | bledin roke cure mhodhake |
| 186 | Chinese (zh) | 26.62 | 7.423 | 1.673 | 32.44 | 0.315 | 0.19 | 0.34 | 1.35 | 2.275 | 1.71 | 162 | ruyifu tryuan plian spobuliang |
| 187 | Galician (gl) | 26.88 | 4.35 | 2.03 | 26.987 | 0.0 | 0.07 | 0.26 | 2.005 | 2.96 | 2.945 | 43 | frenear irar niza ilsitoume |
| 188 | Volapük (vo) | 26.68 | 13.169 | 2.152 | 12.398 | 0.21 | 0.13 | 0.0 | 1.35 | 2.77 | 2.305 | 138 | glemas they jong nuparisville |
| 189 | Cebuano (ceb) | 25.43 | 10.304 | 2.169 | 32.09 | 0.49 | 0.22 | 0.0 | 1.885 | 3.57 | 2.57 | 3 | propet fela akis jeserrell |
| 190 | Wu Chinese (wuu) | 26.97 | 8.398 | 0.968 | 28.333 | 0.21 | 0.075 | 0.0 | 1.465 | 2.195 | 2.05 | 184 | zaizui arsi fire akijikang |
| 191 | Odia (or) | 26.35 | 38.328 | 0.41 | 27.056 | 0.325 | 0.265 | 0.0 | 1.28 | 2.66 | 1.74 | 11 | bebhul tuta bldwara dwamerna |
| 192 | Spanish (es) | 26.73 | 5.046 | 2.0 | 27.885 | 0.205 | 0.225 | 0.32 | 1.74 | 3.01 | 2.985 | 41 | putrero lura ayar unnstarme |
| 193 | Galolen (gal) | 32.68 | 14.301 | 1.183 | 11.765 | 0.0 | 0.035 | 0.0 | 0.305 | 0.505 | 2.945 | 243 | condecedes node adorei xastarraramos |
| 194 | Manx (gv) | 27.9 | 17.925 | 1.183 | 7.351 | 0.28 | 0.27 | 0.0 | 0.75 | 1.485 | 1.725 | 224 | olgaal mulagh ymit joaaddin |
| 195 | Maltese (mt) | 26.59 | 18.673 | 0.793 | 18.212 | 0.085 | 0.245 | 0.09 | 1.64 | 3.04 | 2.735 | 3 | ddevew itat cilu ihaggghlu |
| 196 | Corsican (co) | 27.87 | 9.518 | 1.48 | 12.931 | 0.005 | 0.015 | 0.0 | 1.42 | 2.29 | 3.71 | 139 | giavule ecendu drata uschiunu |
| 197 | Aragonese (an) | 26.74 | 4.778 | 1.914 | 14.6 | 0.13 | 0.07 | 0.0 | 1.775 | 2.725 | 3.235 | 95 | fenidat rien uras idolenta |
| 198 | Ossetic (os) | 28.47 | 19.334 | 0.211 | 5.877 | 0.155 | 0.1 | 0.0 | 0.515 | 0.72 | 2.325 | 297 | dyldaen mury aumae neuarkhaey |
| 199 | Tulu (tcy) | 25.93 | 33.553 | 0.229 | 14.265 | 0.235 | 0.02 | 0.0 | 0.73 | 2.155 | 1.25 | 284 | ndlivat ered iled orsvmbed |
| 200 | Goan Konkani (gom) | 27.64 | 18.502 | 0.856 | 8.85 | 0.24 | 0.2 | 0.0 | 0.935 | 2.11 | 3.695 | 135 | bendcho junk ixcho zholaitolo |
| 201 | Occitan (oc) | 26.63 | 5.118 | 2.15 | 24.22 | 0.215 | 0.145 | 0.0 | 1.755 | 3.855 | 3.655 | 62 | groude ison igat aqnejara |
| 202 | Mizo (lus) | 26.1 | 14.815 | 1.863 | 18.718 | 0.33 | 0.27 | 0.0 | 1.355 | 2.585 | 2.58 | 100 | lortation gata vute cercsaih |
| 203 | Tsonga (ts) | 28.94 | 12.711 | 0.56 | 13.44 | 0.01 | 0.14 | 0.0 | 1.38 | 2.895 | 2.785 | 127 | torela nwanga wine yetsenkulu |
| 204 | Ligurian (lij) | 27.01 | 7.388 | 1.745 | 13.203 | 0.06 | 0.07 | 0.0 | 1.535 | 2.515 | 3.575 | 136 | gandeiva ecca ofon uremoria |
| 205 | Norwegian (no) | 26.65 | 16.05 | 2.514 | 29.189 | 0.58 | 0.415 | 0.17 | 1.385 | 3.75 | 3.26 | 3 | preket lyker dyra knoplitt |
| 206 | Dutch (nl) | 26.84 | 16.258 | 3.536 | 28.796 | 0.77 | 0.265 | 1.215 | 1.235 | 3.59 | 5.1 | 2 | humoot joer gila kwezingsden |
| 207 | Interlingua (ia) | 28.04 | 6.257 | 2.476 | 12.362 | 0.07 | 0.13 | 0.0 | 1.765 | 2.91 | 3.77 | 76 | cumben nual goto rullender |
| 208 | Sami languages (smi) | 26.92 | 13.37 | 0.585 | 4.528 | 0.29 | 0.085 | 0.0 | 1.685 | 3.115 | 2.18 | 155 | kagoat oita ivas kiikkordaga |
| 209 | Indonesian (id) | 26.72 | 7.863 | 2.547 | 32.561 | 0.515 | 0.42 | 0.155 | 1.6 | 2.68 | 3.4 | 5 | himani bluk weir ensiuninya |
| 210 | Klingon (tlh) | 27.88 | 36.287 | 0.283 | 14.709 | 0.065 | 0.025 | 0.0 | 0.115 | 0.295 | 0.73 | 457 | linobij eptlh odtah asriosmoh |
| 211 | West Flemish (vls) | 26.74 | 21.615 | 1.856 | 16.6 | 0.44 | 0.185 | 0.0 | 1.21 | 2.295 | 5.33 | 19 | slogan pign hite tiortica |
| 212 | Pampanga (pam) | 26.05 | 6.147 | 1.939 | 12.784 | 0.48 | 0.06 | 0.0 | 1.68 | 3.135 | 2.99 | 178 | cursus elut ayni kravnine |
| 213 | Lao (lo) | 28.02 | 36.652 | 0.164 | 6.867 | 0.06 | 0.025 | 0.0 | 0.545 | 1.275 | 1.875 | 324 | dvtiti mbav aekan nuetieva |
| 214 | Komi-Permyak (koi) | 26.74 | 15.148 | 0.481 | 6.69 | 0.17 | 0.25 | 0.0 | 0.71 | 1.26 | 2.94 | 259 | rayontsan unodz spiya esrtator |
| 215 | Min Nan Chinese (nan) | 25.67 | 13.275 | 2.16 | 15.728 | 0.445 | 0.255 | 0.0 | 1.695 | 3.68 | 3.185 | 67 | tetrao rute eder clidzery |
| 216 | Swiss German (gsw) | 26.47 | 24.794 | 1.979 | 25.056 | 0.235 | 0.12 | 0.0 | 1.11 | 2.625 | 6.75 | 4 | wolblig guse cape ibureggt |
| 217 | Swedish (sv) | 26.51 | 20.266 | 2.649 | 28.406 | 0.42 | 0.335 | 0.365 | 1.615 | 3.705 | 3.48 | 9 | bittes kvon obade shoreller |
| 218 | French (fr) | 27.21 | 7.026 | 4.156 | 28.618 | 0.745 | 0.425 | 0.475 | 1.805 | 2.97 | 3.52 | 4 | empede jora rune aimonnon |
| 219 | Udmurt (udm) | 26.09 | 19.885 | 0.223 | 6.165 | 0.0 | 0.03 | 0.0 | 0.81 | 1.495 | 2.365 | 359 | uzuran otsa uysy zakschan |
| 220 | Banjar (bjn) | 27.04 | 14.771 | 1.036 | 9.824 | 0.135 | 0.02 | 0.0 | 1.145 | 2.32 | 2.68 | 307 | ngkalat elut yakan nurnmbat |
| 221 | Western Mari (mrj) | 27.73 | 31.322 | 0.444 | 6.091 | 0.085 | 0.02 | 0.0 | 0.705 | 1.99 | 1.335 | 383 | kisten gimy emash aznikten |
| 222 | Hausa (ha) | 26.36 | 3.154 | 0.81 | 19.837 | 0.245 | 0.135 | 0.0 | 1.76 | 2.62 | 2.91 | 189 | junyun cema imen nonnabai |
| 223 | Aymara (ay) | 37.84 | 14.457 | 0.263 | 7.314 | 0.0 | 0.065 | 0.0 | 0.195 | 0.255 | 5.655 | 104 | mirkataki biana enakama dithapanakaru |
| 224 | Mazanderani (mzn) | 25.57 | 73.502 | 0.022 | 17.36 | 0.005 | 0.02 | 0.0 | 0.095 | 0.48 | 0.095 | 373 | amwdabd andy nhmyn zmanhtly |
| 225 | Iloko (ilo) | 26.0 | 5.52 | 1.164 | 11.032 | 0.13 | 0.035 | 0.0 | 2.09 | 3.335 | 3.11 | 159 | ukabor gela ubat fabunisia |
| 226 | Malay (ms) | 26.63 | 7.113 | 2.474 | 32.76 | 0.67 | 0.455 | 0.22 | 1.95 | 3.345 | 3.29 | 5 | graying ciat aukan viendilah |
| 227 | Erzya (myv) | 27.69 | 30.597 | 0.554 | 7.877 | 0.0 | 0.03 | 0.0 | 1.03 | 1.85 | 1.76 | 320 | eshuat adste ivms dazytaks |
| 228 | German (de) | 26.88 | 22.75 | 2.648 | 24.144 | 0.61 | 0.115 | 0.585 | 1.49 | 2.94 | 5.605 | 41 | chorungen goon puschen oracemische |
| 229 | Vietnamese (vi) | 25.22 | 12.89 | 3.892 | 33.284 | 0.845 | 0.355 | 0.49 | 2.145 | 4.105 | 2.565 | 17 | neandan khau exin slockani |
| 230 | Northern Frisian (frr) | 27.24 | 22.601 | 2.685 | 13.495 | 0.6 | 0.27 | 0.0 | 1.08 | 2.47 | 2.97 | 196 | trotem uunis knap foorolais |
| 231 | English (en) | 26.19 | 14.008 | 5.947 | 33.414 | 0.885 | 0.545 | 0.885 | 1.745 | 3.79 | 3.04 | 1 | kageous cers atty gilmutation |
| 232 | Bavarian (bar) | 26.39 | 30.395 | 1.197 | 27.352 | 0.32 | 0.075 | 0.0 | 1.13 | 2.63 | 7.53 | 6 | sunsde jont lutz thonfene |
| 233 | Kabardian (kbd) | 31.18 | 39.293 | 0.163 | 7.228 | 0.0 | 0.02 | 0.0 | 0.33 | 0.645 | 1.29 | 387 | femyde kikhyu iiashch ushygygekher |
| 234 | Kabiyè (kbp) | 26.24 | 15.302 | 0.477 | 18.741 | 0.17 | 0.13 | 0.0 | 1.075 | 1.965 | 1.99 | 362 | ecsoki nvyi jasi ruolaton |
| 235 | Interlingue (ie) | 26.36 | 14.111 | 3.0 | 8.278 | 0.35 | 0.265 | 0.0 | 1.535 | 3.29 | 3.005 | 177 | lorcar ocon elat undonctiones |
| 236 | Konkani (individual language) (knn) | 25.52 | 70.078 | 0.05 | 19.383 | 0.0 | 0.0 | 0.0 | 0.155 | 0.65 | 0.235 | 418 | sftrydh hyym azdgn nqilysth |
| 237 | Middle French (frm) | 34.74 | 13.326 | 0.887 | 8.144 | 0.0 | 0.085 | 0.0 | 0.075 | 0.21 | 7.365 | 159 | dattoit gres ouassiez erendasses |
| 238 | Central Bikol (bcl) | 26.08 | 8.063 | 1.387 | 10.093 | 0.235 | 0.2 | 0.0 | 1.99 | 3.235 | 2.435 | 173 | dukiro wado awan syhitood |
| 239 | Karachay-Balkar (krc) | 27.15 | 20.462 | 0.612 | 3.678 | 0.0 | 0.115 | 0.0 | 1.125 | 1.955 | 2.44 | 336 | aktoan noly peda tsiarlege |
| 240 | Italian (it) | 27.57 | 5.634 | 2.181 | 25.728 | 0.52 | 0.405 | 0.55 | 2.095 | 3.635 | 4.53 | 22 | agason irne otato ileservate |
| 241 | Neapolitan (nap) | 29.24 | 6.906 | 4.038 | 10.732 | 0.145 | 0.17 | 0.0 | 1.74 | 2.39 | 5.69 | 104 | aummastevo ecave uete nfrivosine |
| 242 | Haitian Creole (ht) | 26.82 | 12.651 | 1.521 | 12.951 | 0.13 | 0.36 | 0.0 | 1.235 | 2.475 | 2.355 | 300 | datwen obis vyon swounden |
| 243 | Maithili (mai) | 26.08 | 42.105 | 0.294 | 12.621 | 0.3 | 0.18 | 0.0 | 1.05 | 2.68 | 1.355 | 334 | yurthk pork kyati rupisndime |
| 244 | Tigre (tig) | 25.7 | 41.614 | 0.305 | 13.923 | 0.09 | 0.01 | 0.0 | 0.67 | 1.28 | 1.24 | 490 | musakin rhew nhze gwedzete |
| 245 | Zeelandic (zea) | 26.46 | 21.433 | 1.75 | 11.638 | 0.25 | 0.09 | 0.0 | 1.355 | 2.365 | 4.6 | 322 | enweege kund juel muwerine |
| 246 | Old French (fro) | 33.21 | 8.034 | 0.665 | 17.981 | 0.04 | 1.12 | 0.0 | 0.15 | 0.225 | 6.35 | 16 | nuloierent elons eussiez jaucouroies |
| 247 | Colognian (ksh) | 26.02 | 28.964 | 1.832 | 15.701 | 0.46 | 0.225 | 0.0 | 1.095 | 2.74 | 3.64 | 387 | suritz auld orer amooddin |
| 248 | Fiji Hindi (hif) | 25.3 | 22.806 | 2.369 | 13.5 | 0.635 | 0.235 | 0.0 | 1.46 | 3.43 | 2.145 | 423 | noilian avte phes elowlison |
| 249 | Quechua (qu) | 36.28 | 13.689 | 0.531 | 5.939 | 0.0 | 0.265 | 0.0 | 0.31 | 0.445 | 8.735 | 203 | ukyuqa zepaq tshina meawchachun |
| 250 | Palatine German (pfl) | 27.14 | 35.018 | 1.476 | 11.976 | 0.335 | 0.145 | 0.0 | 1.095 | 2.53 | 9.015 | 301 | kimide earn esisch ehehrach |
| 251 | Māori (mi) | 28.25 | 1.359 | 1.296 | 17.793 | 0.065 | 0.115 | 0.0 | 0.75 | 1.59 | 23.67 | 113 | deapoto elenga exka quihouroa |

Columns:
- **chars**: average characters per phrase.
- **3+ cons. %**: words with 3+ consonants in a row.
- **EN words %**: words that are real English words.
- **own words %**: words that are real words of the table's language(s).
- **EN list %**: phrases with a whole word from an English offensive list.
- **EN severe %**: phrases with a severe English term (whole, or inside a word if 5+ letters).
- **own list %**: phrases with a whole word from the table language's own list.
- **major lists %**: phrases with a whole word from the lists of 13 most-spoken languages.
- **any list %**: phrases with a whole word from any language's list.
- **inside 5+ %**: phrases with a listed term of 5+ letters inside a word.
- **relaxed rows**: table rows (of 768) that needed the join rule relaxed.

Failed builds: klr (ValueError('not enough prefix-free tokens'))
