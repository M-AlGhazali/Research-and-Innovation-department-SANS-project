"""Image-assisted transcription of the four supplied A1 PDFs, checked 2026-10-26.
The PDFs have image tables, not extractable text. Source '-' cells stay '-'.
Row tokens: fix path magnetic true variation distance turn altitude speed flyover.
Repeated trunks below were checked on each procedure, not inferred from the map.
"""
COORDS = '''
BOMOX 22 29 49 038 27 04
DATAP 22 39 27 039 29 10
DENBU 21 01 29 038 20 31
EGPOB 20 55 28 039 47 10
EGREP 22 27 54 039 50 07
ISLAM 21 46 48 039 52 00
KAROX 20 57 17 038 15 47
MIGDA 22 38 29 038 42 53
RIBAM 20 42 31 039 05 51
JN274 22 21 30 038 42 47
JN234 22 15 36 038 53 54
JN259 21 06 12 039 32 05
JN383 22 09 53 038 56 37
JN520 22 23 57 039 31 45
JN522 21 19 57 039 01 07
JN610 21 38 33 038 42 25
NIVBA 21 47 22 038 49 56
ASPAG 22 04 13 038 43 01
JN254 21 53 47 039 04 19
JN276 22 00 23 039 01 10
JN510 22 33 59 039 22 51
JN521 21 10 31 039 04 45
JN530 22 11 32 039 24 12
JN733 21 23 30 038 29 36
RALVI 22 18 02 039 04 30
JN264 21 40 16 038 53 30
JN266 22 09 46 038 40 10
JN272 21 46 09 039 05 07
JN278 21 19 58 038 36 11
JN279 21 16 27 038 33 12
JN382 21 10 17 038 41 32
JN385 21 04 56 038 46 19
JN390 21 06 17 038 59 28
JN395 21 01 35 039 20 19
ORSOD 21 52 53 038 56 29
SERSO 22 04 11 038 51 06
'''
C_LIST = ['JN274','BOMOX','DENBU','EGREP','JN234','JN259','JN383','JN520','JN522','JN610','KAROX','NIVBA','RIBAM','ASPAG','DATAP','EGPOB','ISLAM','JN254','JN276','JN510','JN521','JN530','JN733','MIGDA','RALVI']
L_LIST = ['BOMOX','DATAP','DENBU','EGPOB','EGREP','ISLAM','JN264','JN266','JN272','JN278','JN279','JN382','JN383','JN385','JN390','JN395','JN510','JN520','JN530','ORSOD','KAROX','RALVI','RIBAM','SERSO']
C0 = '''JN254 CF 336 339.7 -3.8 12.8 - - - -
JN276 TF 332 336.0 -3.8 7.2 - @6000 - -
JN383 TF 332 336.0 -3.8 10.4 - - - -'''
L0 = '''JN272 CF 326 329.7 -3.8 4.6 - +1500 -210 Y'''
LN = L0 + '\nORSOD CF 305 309.1 -3.8 - - -6000 - -\nSERSO TF 332 336.1 -3.8 12.3 - - - -'
LS = L0 + '\nJN264 CF 227 230.4 -3.8 - - -6000 - -\nJN278 TF 215 218.7 -3.8 25.9 - - - -'
CLEFT = '''ASPAG TF 242 245.9 -3.8 13.8 L - - -
NIVBA TF 155 159.0 -3.8 18.0 - - - -'''
CNORTH = '''RALVI TF 038 042.0 -3.8 10.9 - - - -'''
LNORTH = '''JN383 TF 038 042.0 -3.8 7.6 - - - -
RALVI TF 038 042.0 -3.8 10.9 - - - -'''
ROWS = {
('34C','ISLAM 2W'): C0+'\n'+CNORTH+'''
JN530 TF 106 109.5 -3.8 19.4 - - - -
ISLAM TF 130 133.6 - 35.7 - -13000 - -''',
('34C','EGREP 2W'): C0.replace('-3.8','3.8')+'\n'+CNORTH.replace('-3.8','3.8')+'''
JN520 TF 073 076.8 3.8 25.9 - -13000 - -
EGREP TF 073 076.9 - 17.5 - - - -''',
('34C','DATAP 2W'): C0+'\n'+CNORTH+'''
JN510 TF 043 046.9 -3.8 23.3 - -13000 - -
DATAP TF 043 047.0 - 8.0 - - - -''',
('34C','MIGDA 2W'): C0+'''
JN234 TF 332 336.1 -3.8 6.2 - - - -
MIGDA TF 332 335.9 - 25.0 - - - -''',
('34C','BOMOX 2W'): C0+'''
JN234 TF 332 336.1 -3.8 6.2 - - - -
JN274 TF 296 299.8 -3.8 11.8 - - - -
BOMOX TF 296 299.7 - 16.7 - - - -''',
('34C','EGPOB 2W'): C0.rsplit(' - - - -',1)[0]+' L - - -\n'+CLEFT+'''
JN522 TF 155 159.1 -3.8 29.2 - -9000 - -
JN521 TF 155 159.1 -3.8 10.1 - @12000 - -
JN259 TF 096 099.5 -3.8 25.7 - - - -
EGPOB TF 123 127.1 - 17.7 - - - -''',
('34C','RIBAM 2W'): C0.replace('339.7 -3.8','339.7 3.8').rsplit(' - - - -',1)[0]+' L - - -\n'+CLEFT+'''
JN522 TF 155 159.1 -3.8 29.2 - -9000 - -
JN521 TF 155 159.1 -3.8 10.1 - @12000 - -
RIBAM TF 174 178.3 - 27.9 - - - -''',
('34C','KAROX 2W'): C0.rsplit(' - - - -',1)[0]+' L - - -\n'+CLEFT+'''
JN610 TF 215 218.6 -3.8 11.2 - -12000 - -
JN733 TF 215 218.6 -3.8 19.2 - - - -
DENBU TF 197 201.2 -3.8 23.5 - - - -
KAROX TF 223 226.6 - 6.1 - - - -''',
('34L','ISLAM 3X'): LN+'\n'+LNORTH+'''
JN530 TF 106 109.5 -3.8 19.4 - -13000 - -
ISLAM TF 130 133.6 -3.8 35.7 - -13000 - -''',
('34L','EGREP 3X'): LN+'\n'+LNORTH+'''
JN520 TF 073 076.8 -3.8 25.9 - -13000 - -
EGREP TF 073 076.9 -3.8 17.5 - - - -''',
('34L','DATAP 3X'): LN+'\n'+LNORTH+'''
JN510 TF 043 046.9 -3.8 23.3 - -13000 - -
DATAP TF 043 047.0 -3.8 8.0 - - - -''',
('34L','BOMOX 3X'): LN.replace('12.3 - - - -','12.3 - -12000 - -')+'''
JN266 TF 295 298.8 -3.8 11.6 - - - -
BOMOX TF 325 328.8 -3.8 23.4 - - - -''',
('34L','EGPOB 3X'): LS+'''
JN382 TF 149 152.6 -3.8 10.9 - - - -
JN390 TF 100 103.3 -3.8 17.2 - @12000 - -
JN395 TF 100 103.4 -3.8 20.1 - +FL160 - -
EGPOB TF 100 103.6 -3.8 25.8 - - - -''',
('34L','RIBAM 3X'): LS+'''
JN382 TF 149 152.6 -3.8 10.9 - - - -
JN385 TF 136 140.0 -3.8 7.0 - @12000 - -
RIBAM TF 137 140.6 -3.8 28.9 - - - -''',
('34L','KAROX 3X'): LS+'''
JN279 TF 215 218.5 -3.8 4.5 - -12000 - -
DENBU TF 215 218.5 -3.8 19.0 - - - -
KAROX TF 223 226.6 -3.8 6.1 - - - -''',
('34L','MIGDA 3X'): LN.replace('12.3 - - - -','12.3 - -12000 - -')+'''
JN274 TF 332 335.9 -3.8 18.9 - - - -
MIGDA TF 357 000.3 -3.8 16.9 - - - -'''
}
# Literal routing text, with PDF line wraps collapsed to spaces. Visible typos retained.
TEXT = {
'BOMOX 2W':'Climb to JN254 on course 336°, to JN276 at 6000ft, to JN383, to JN234, turn left to JN274, to BOMOX',
'DATAP 2W':'Climb to JN254 on course 336°, to JN276 at 6000ft, to JN383, turn right to RALVI, to JN510 at or below 13000ft, to DATAP',
'EGPOB 2W':'Climb to JN254 on course 336°, to JN276 at 6000ft, to JN383, turn left to ASPAG, turn left to NIVBA, to JN522 at or below 9000ft, to JN521 at 12000ft, turn left to JN259, turn right to EGPOB',
'EGREP 2W':'Climb to JN254 on course 336°, to JN276 at 6000ft, to JN383, turn right to RALVI, to JN520 at or below 13000ft, to EGREP',
'ISLAM 2W':'Climb to JN254 on course 336°, to JN276 at 6000ft, to JN383, turn right to RALVI, turn right to JN530, turn right to ISLAM at or below 13000ft',
'KAROX 2W':'Climb to JN254 on course 336°, to JN276 at 6000ft, to JN383, turn left to ASPAG, turn left to NIVBA, turn right to JN610 at or below 12000ft, to JN733, turn left to DENBU, turn right to KAROX',
'MIGDA 2W':'Climb to JN254 on course 336°, turn left to JN276 at 6000ft, to JN383, to JN234, to MIGDA',
'RIBAM 2W':'Climb to JN254 on course 336°, to JN276 at 6000ft, to JN383, turn left to ASPAG, turn left to NIVBA, to JN522 at or below 9000ft, to JN521 at 12000ft, and turn right to RIBAM',
'BOMOX 3X':'Climb to JN272 on course 326° at or above 1500ft, maximum speed 210 kts, turn left to ORSOD on course 305° at or below 6000ft, turn right to SERSO at or below 12000ft, turn left to JN266, turn right to BOMOX',
'DATAP 3X':'Climb to JN272 on course 326° at or above 1500ft, maximum speed 210 kts, turn left to ORSOD on course305° at or below 6000ft, turn right to SERSO, turn right to JN383, to RALVI, to JN510 at or below 13000ft, to DATAP',
'EGPOB 3X':'Climb to JN272 on course 326° at or above 1500ft, maximum speed 210 kts, turn left to JN264 on course 227° at or below 6000ft, to JN278, turn left to JN382, turn left to JN390 at 12000ft, to JN395 at or above FL160, toEGPOB',
'EGREP 3X':'Climb to JN272 on course 326° at or above 1500ft, maximum speed 210 kts, turn left to ORSOD on course305° at or below 6000ft, turn right to SERSO, turn right to JN383, to RALVI, turn right to JN520 at or below 13000ft,to EGREP.',
'ISLAM 3X':'Climb to JN272 on course 326° at or above 1500ft, maximum speed 210 kts, turn left to ORSOD on course 305° at or below 6000ft, turn right to SERSO, turn right to JN383, to RALVI, turn right to JN530 at or below 13000ft,turn right to ISLAM at or below 13000ft',
'KAROX 3X':'Climb to JN272 on course 326° at or above 1500ft, maximum speed 210 kts, turn left to JN264 on course 227° at or below 6000ft, to JN278, to JN279 at or below 12000ft, to DENBU, t to KAROX',
'MIGDA 3X':'Climb to JN272 on course 326° at or above 1500ft, maximum speed 210 kts, turn left to ORSOD on course 305° at or below 6000ft, turn right to SERSO at or below 12000ft, to JN274, turn right to MIGDA',
'RIBAM 3X':'Climb to JN272 on course 326° at or above 1500ft, maximum speed 210 kts, turn left to JN264 on course 227° at or below 6000ft, to JN278, turn left to JN382, turn left to JN385 at 12000ft, to RIBAM.'
}
