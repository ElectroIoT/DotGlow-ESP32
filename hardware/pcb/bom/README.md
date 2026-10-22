# DotGlow V1 board: bill of materials

22 lines, 58 parts. All parts are on LCSC (JLCPCB assembly) except the test points (just pads).

| File | Use |
|---|---|
| [`dotglow-v1-bom.xlsx`](dotglow-v1-bom.xlsx) | the BOM exported from EasyEDA (upload this to JLCPCB / PCBWay assembly) |
| [`dotglow-v1-bom.csv`](dotglow-v1-bom.csv) | the same list as plain text |

**Not on the BOM:** the 4-in-1 MAX7219 LED matrix module, the 8 ohm 2 W speaker, the push button, LDR and DHT22
(they plug into the JST XA connectors). The ESP32-S3-WROOM-1 module (U1, C2913202) can be left off the assembly
order if you already own one.

| # | Qty | Part | Designators | Package | LCSC |
|--:|--:|---|---|---|---|
| 1 | 4 | 100nF | C1,C2,C6,C9 | C0805 | C49678 |
| 2 | 1 | 1uF | C3 | C0805 | C344178 |
| 3 | 4 | 10uF | C4,C5,C7,C8 | C0805 | C440198 |
| 4 | 2 | 100uF | C10,C11 | CAP-SMD_BD6.3-L6.6-W6.6-LS7.2-FD | C970686 |
| 5 | 1 | B04B-XASK-1-A(LF)(SN) | CN1 | CONN-TH_B04B-XASK-1-A-LF-SN | C491709 |
| 6 | 2 | SS34 | D1,D2 | SMA_L4.3-W2.6-LS5.2-RD | C8678 |
| 7 | 1 | PZ254V-11-05P | H1 | HDR-TH_5P-P2.54-V-M | C492404 |
| 8 | 1 | XC6220B331MR-G | Q1 | SOT-25_L3.0-W1.6-P0.95-LS2.8-TL | C86534 |
| 9 | 4 | 100Ω | R1,R2,R3,R13 | R0805 | C105577 |
| 10 | 3 | 5.1kΩ | R4,R6,R7 | R0805 | C27834 |
| 11 | 1 | 100kΩ | R5 | R0805 | C149504 |
| 12 | 3 | 10kΩ | R8,R9,R12 | R0805 | C17414 |
| 13 | 2 | 4.7kΩ | R10,R11 | R0805 | C2907264 |
| 14 | 2 | TSB001A3512A | SW1,SW2 | SW-SMD_TSB001XXXX | C2888948 |
| 15 | 16 | Test-Point | TP1,TP2,TP3,TP4,TP5,TP6,TP7,TP8,TP9,TP10,TP11,TP12,TP13,TP14,TP15,TP16 | Test-Point-0.5mm |  |
| 16 | 1 | 2.4GHz | U1 | WIRELM-SMD_ESP32-S3-WROOM-1 | C2913202 |
| 17 | 2 | XL-B1515RGBA-HF | U2,U8 | LED-SMD_4P-L1.6-W1.5_WHITE-LED | C22461781 |
| 18 | 4 | B02B-XASK-1-A(LF)(SN) | U3,U4,U5,U10 | CONN-TH_B02B-XASK-1-A-LF-SN | C265077 |
| 19 | 1 | B03B-XASK-1(LF)(SN) | U6 | CONN-TH_B03B-XASK-1-LF-SN | C265055 |
| 20 | 1 | MAX98357AETE+T | U7 | TQFN-16_L3.0-W3.0-P0.50-BL-EP1.5 | C910544 |
| 21 | 1 | SN74AHCT125DR | U9 | SOIC-14_L8.7-W3.9-P1.27-LS6.0-BL | C155176 |
| 22 | 1 | TYPE-C 16PIN 2MD(073) | USB1 | USB-C-SMD_TYPE-C-16PIN-2MD-073 | C2765186 |
