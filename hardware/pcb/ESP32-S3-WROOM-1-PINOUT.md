# ESP32-S3-WROOM-1-N16R8 (LCSC C2913202) pinout and DotGlow V1 connections

Source: Espressif datasheet ESP32-S3-WROOM-1 / WROOM-1U v1.3 (table 3, section 3.3). Module 25.5 x 18 mm, PCB antenna,
16 MB flash, 8 MB **octal** PSRAM (so IO35, IO36, IO37 are used inside the module and cannot be used).

Pin numbers: 1-14 left side (top to bottom), 15-26 bottom, 27-40 right side (bottom to top), 41 = EPAD (ground, centre).
Antenna at the top. Pin 1 is the top-left pin next to the antenna.

| Pin | Name | Type | Functions (default first) | DotGlow V1 net / use |
|---|---|---|---|---|
| 1 | GND | P | ground | GND |
| 2 | 3V3 | P | 3.3 V supply (3.0 to 3.6 V, at least 500 mA) | +3V3 from the XC6220 regulator |
| 3 | EN | I | chip enable (high = on). **Must not float** | EN: 10k to 3V3, 1 uF to GND, RESET button |
| 4 | IO4 | I/O | GPIO4, TOUCH4, ADC1_CH3 | STOPWATCH (button SW3 and header J7) |
| 5 | IO5 | I/O | GPIO5, TOUCH5, ADC1_CH4 | I2S_BCLK to MAX98357A |
| 6 | IO6 | I/O | GPIO6, TOUCH6, ADC1_CH5 | I2S_LRC to MAX98357A |
| 7 | IO7 | I/O | GPIO7, TOUCH7, ADC1_CH6 | I2S_DIN to MAX98357A |
| 8 | IO15 | I/O | GPIO15, U0RTS, ADC2_CH4, XTAL_32K_P | AMP_SD (amplifier mute) |
| 9 | IO16 | I/O | GPIO16, U0CTS, ADC2_CH5, XTAL_32K_N | not used (free) |
| 10 | IO17 | I/O | GPIO17, U1TXD, ADC2_CH6 | not used (free) |
| 11 | IO18 | I/O | GPIO18, U1RXD, ADC2_CH7 | not used (free) |
| 12 | IO8 | I/O | GPIO8, TOUCH8, ADC1_CH7 | I2C_SDA (header J4, RTC in V2) |
| 13 | **IO19 = USB_D-** | I/O | GPIO19, U1RTS, ADC2_CH8, **USB_D-** | **USB-C D- (through the ESD chip)** |
| 14 | **IO20 = USB_D+** | I/O | GPIO20, U1CTS, ADC2_CH9, **USB_D+** | **USB-C D+ (through the ESD chip)** |
| 15 | IO3 | I/O | GPIO3, TOUCH3, ADC1_CH2 (JTAG-source strap) | not used, leave free |
| 16 | IO46 | I/O | GPIO46 (strap, default low) | not used, leave free |
| 17 | IO9 | I/O | GPIO9, TOUCH9, ADC1_CH8 | I2C_SCL (header J4) |
| 18 | IO10 | I/O | GPIO10, TOUCH10, FSPICS0 | MAX_CS_3V (SPI CS, `PIN_CS`) |
| 19 | IO11 | I/O | GPIO11, TOUCH11, FSPID | MAX_DIN_3V (SPI MOSI) |
| 20 | IO12 | I/O | GPIO12, TOUCH12, FSPICLK | MAX_CLK_3V (SPI CLK) |
| 21 | IO13 | I/O | GPIO13, TOUCH13, FSPIQ | DHT_DATA (optional DHT22) |
| 22 | IO14 | I/O | GPIO14, TOUCH14, FSPIWP | not used (free) |
| 23 | IO21 | I/O | GPIO21 | not used (free) |
| 24 | IO47 | I/O | GPIO47, SPICLK_P_DIFF | not used (free) |
| 25 | IO48 | I/O | GPIO48, SPICLK_N_DIFF | not used (free) |
| 26 | IO45 | I/O | GPIO45 (strap, VDD_SPI voltage, default low) | not used, leave free |
| 27 | IO0 | I/O | GPIO0 (strap: low at reset = download mode) | BOOT button (SW2); firmware `PIN_BUTTON` |
| 28 | IO35 | I/O | SPIIO6 | **not usable (octal PSRAM)**, leave unconnected |
| 29 | IO36 | I/O | SPIIO7 | **not usable (octal PSRAM)**, leave unconnected |
| 30 | IO37 | I/O | SPIDQS | **not usable (octal PSRAM)**, leave unconnected |
| 31 | IO38 | I/O | GPIO38, FSPIWP | not used (free) |
| 32 | IO39 | I/O | MTCK, GPIO39 | not used (JTAG, free) |
| 33 | IO40 | I/O | MTDO, GPIO40 | not used (JTAG, free) |
| 34 | IO41 | I/O | MTDI, GPIO41 | not used (JTAG, free) |
| 35 | IO42 | I/O | MTMS, GPIO42 | not used (JTAG, free) |
| 36 | RXD0 | I/O | U0RXD, GPIO44 | not used (UART0, free; USB is used for logs) |
| 37 | TXD0 | I/O | U0TXD, GPIO43 | not used (UART0, free) |
| 38 | IO2 | I/O | GPIO2, TOUCH2, ADC1_CH1 | NTC_ADC (10k NTC divider) |
| 39 | IO1 | I/O | GPIO1, TOUCH1, ADC1_CH0 | LDR_ADC (`PIN_LDR`, optional LDR) |
| 40 | GND | P | ground | GND |
| 41 | EPAD | P | ground (centre pad) | GND, tie to the ground plane with several vias |

GPIO26 to GPIO32 are not available on this module (they are used by the flash).

## Where D+ and D- go

- **USB-C D+ (A6/B6) to pin 14 (IO20 = USB_D+)** and **USB-C D- (A7/B7) to pin 13 (IO19 = USB_D-)**.
- Join the two D+ pins of the USB-C connector together, and the two D- pins together, so the cable works either way up.
- Put the ESD chip (USBLC6-2SC6) right next to the USB-C connector, in line with the D+ / D- tracks.
- Keep the two tracks short, side by side and the same length. No series resistors are needed (an optional 22 to 33 ohm in each line is fine).
- GPIO19 and GPIO20 cannot be used for anything else while USB is used.
- With the USB-C connector you can flash the firmware and read the serial log without a USB-UART chip: hold BOOT (GPIO0), tap RESET (EN), release BOOT.

## Other connections you must make

- **EN**: 10k pull-up to 3V3, 1 uF to GND, and the RESET button to GND. Do not leave it floating.
- **GPIO0 (pin 27)**: BOOT button to GND. Do not pull it low externally during normal start-up.
- **Pins 1, 40 and 41**: all to GND, pin 41 (EPAD) with several vias to the ground plane.
- **3V3 (pin 2)**: 22 uF + 100 nF close to the pin, regulator rated at least 500 mA (XC6220B331MR-G is 1 A).
- **Strapping pins** IO0, IO3, IO45, IO46: leave IO3, IO45, IO46 unconnected so their defaults apply.
- **Antenna**: no copper, tracks, vias, speaker or metal under or near the antenna end (the top 6.5 mm of the module and a few mm beyond).
- Placed with the antenna end hanging at the board edge, or inside the keep-out at the board edge.
