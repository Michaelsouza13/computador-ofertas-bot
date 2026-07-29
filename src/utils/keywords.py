HARDWARE_KEYWORDS = {
    "cpu": [
        "processador", "ryzen", "intel core", "i5", "i7", "i9", "ultra 5", "ultra 7", "ultra 9",
        "amd ryzen", "socket am5", "socket am4", "lga 1700", "lga 1851",
    ],
    "gpu": [
        "placa de video", "placa de vídeo", "geforce", "rtx", "gtx", "radeon", "rx",
        "nvidia", "amd radeon", "intel arc", "rtx 40", "rtx 50", "rx 70", "rx 90",
    ],
    "ram": [
        "memoria ram", "memória ram", "ddr4", "ddr5", "16gb", "32gb", "64gb",
        "kingston fury", "corsair vengeance", "xpg", "g.skill",
    ],
    "ssd": [
        "ssd", "nvme", "m.2", "sata ssd", "armazenamento", "1tb", "2tb",
        "kingston nv2", "wd black", "samsung 990", "crucial",
    ],
    "motherboard": [
        "placa mae", "placa mãe", "motherboard", "b650", "b760", "x670", "z790",
        "x870", "a620", "h610", "chipset am5", "chipset lga",
    ],
    "psu": [
        "fonte", "psu", "corsair", "evga", "cooler master", "xpg", "750w", "850w",
        "1000w", "fonte modular", "fonte atx 3.0",
    ],
    "case": [
        "gabinete", "case", "mid tower", "full tower", "gamer", "lian li",
        "corsair", "nzxt", "rise mode", "aquário",
    ],
    "cooler": [
        "water cooler", "air cooler", "cooler cpu", "ventoinha", "fan",
        "deepcool", "corsair h", "noctua", "thermalright",
    ],
}

ALL_HARDWARE = [
    kw for category in HARDWARE_KEYWORDS.values() for kw in category
]
