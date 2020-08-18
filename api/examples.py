import requests, json

config = json.dumps(
    {
        "camera": {
        "camera1": {
            "desc": "FLI Microline e2vU42DD",
            "driver": "ASCOM.Simulator.Camera",
            "name": "simulator_camera",
            "parent": "telescope1",
            "settings": {
            "area": [
                "100%",
                "2X-jpg",
                "71%",
                "50%",
                "1X-jpg",
                "33%",
                "25%",
                "1/2 jpg"
            ],
            "bin_modes": [
                [
                "1",
                "1"
                ],
                [
                "2",
                "2"
                ]
            ],
            "can_subframe": "true",
            "east_offset": "0.0",
            "has_darkslide": "false",
            "has_screen": "true",
            "is_cmos": "false",
            "max_exposure": "600.0",
            "min_exposure": "0.100",
            "min_subframe": "16:16",
            "north_offset": "0.0",
            "overscan_x": "0",
            "overscan_y": "0",
            "reference_dark": [
                "0.2",
                "-30"
            ],
            "reference_gain": [
                "1.4",
                "1.4"
            ],
            "reference_noise": [
                "14.0",
                "14.0"
            ],
            "rotation": "0.0",
            "screen_settings": {
                "screen_saturation": "157.0",
                "screen_x0": "8.683",
                "screen_x1": ".1258",
                "screen_x2": "-9E-05",
                "screen_x3": "3E-08",
                "screen_x4": "-4E-12"
            },
            "x_pixel": "13.5",
            "x_start": "0",
            "x_width": "2048",
            "y_pixel": "13.5",
            "y_start": "0",
            "y_width": "2048"
            }
        }
        },
        "defaults": {
        "camera": "camera1",
        "enclosure": "enclosure1",
        "filter_wheel": "filter_wheel1",
        "focuser": "focuser1",
        "mount": "mount1",
        "rotator": "rotator1",
        "screen": "screen1",
        "sequencer": "sequencer1",
        "telescope": "telescope1"
        },
        "elevation": "5100",
        "enclosure": {
        "enclosure1": {
            "controlled_by": [
            "mnt1"
            ],
            "driver": "ASCOM.Simulator.Dome",
            "has_lights": "true",
            "is_dome": "true",
            "name": "SinDome",
            "parent": "site",
            "settings": {
            "lights": [
                "Auto",
                "White",
                "Red",
                "IR",
                "Off"
            ],
            "roof_shutter": [
                "Auto",
                "Open",
                "Close",
                "Lock Closed",
                "Unlock"
            ]
            }
        }
        },
        "filter_wheel": {
        "filter_wheel1": {
            "desc": "FLI Centerline Custom Dual 50mm sq.",
            "driver": [
            "ASCOM.Simulator.FilterWheel",
            "ASCOM.Simulator.FilterWheel"
            ],
            "name": "Dual filter wheel",
            "parent": "tel1",
            "settings": {
            "filter_count": "23",
            "filter_data": [
                [
                "filter",
                "filter_index",
                "filter_offset",
                "sky_gain",
                "screen_gain",
                "abbreviation"
                ],
                [
                "air",
                "(0, 0)",
                "-1000",
                "0.01",
                "790",
                "ai"
                ],
                [
                "dif",
                "(4, 0)",
                "0",
                "0.01",
                "780",
                "di"
                ],
                [
                "w",
                "(2, 0)",
                "0",
                "0.01",
                "780",
                "w_"
                ],
                [
                "ContR",
                "(1, 0)",
                "0",
                "0.01",
                "175",
                "CR"
                ],
                [
                "N2",
                "(3, 0)",
                "0",
                "0.01",
                "101",
                "N2"
                ],
                [
                "u",
                "(0, 5)",
                "0",
                "0.01",
                "0.2",
                "u_"
                ],
                [
                "g",
                "(0, 6)",
                "0",
                "0.01",
                "550",
                "g_"
                ],
                [
                "r",
                "(0, 7)",
                "0",
                "0.01",
                "630",
                "r_"
                ],
                [
                "i",
                "(0, 8)",
                "0",
                "0.01",
                "223",
                "i_"
                ],
                [
                "zs",
                "(5, 0)",
                "0",
                "0.01",
                "15.3",
                "zs"
                ],
                [
                "PL",
                "(0, 4)",
                "0",
                "0.01",
                "775",
                "PL"
                ],
                [
                "PR",
                "(0, 3)",
                "0",
                "0.01",
                "436",
                "PR"
                ],
                [
                "PG",
                "(0, 2)",
                "0",
                "0.01",
                "446",
                "PG"
                ],
                [
                "PB",
                "(0, 1)",
                "0",
                "0.01",
                "446",
                "PB"
                ],
                [
                "O3",
                "(7, 0)",
                "0",
                "0.01",
                "130",
                "03"
                ],
                [
                "HA",
                "(6, 0)",
                "0",
                "0.01",
                "101",
                "HA"
                ],
                [
                "S2",
                "(8, 0)",
                "0",
                "0.01",
                "28",
                "S2"
                ],
                [
                "dif_u",
                "(4, 5)",
                "0",
                "0.01",
                "0.2",
                "du"
                ],
                [
                "dif_g",
                "(4, 6)",
                "0",
                "0.01",
                "515",
                "dg"
                ],
                [
                "dif_r",
                "(4, 7)",
                "0",
                "0.01",
                "600",
                "dr"
                ],
                [
                "dif_i",
                "(4, 8)",
                "0",
                "0.01",
                "218",
                "di"
                ],
                [
                "dif_zs",
                "(9, 0)",
                "0",
                "0.01",
                "14.5",
                "dz"
                ],
                [
                "dark",
                "(10, 9)",
                "0",
                "0.01",
                "0.0",
                "dk"
                ]
            ],
            "filter_reference": "2",
            "filter_screen_sort": [
                "0",
                "1",
                "2",
                "10",
                "7",
                "19",
                "6",
                "18",
                "12",
                "11",
                "13",
                "8",
                "20",
                "3",
                "14",
                "15",
                "4",
                "16",
                "9",
                "21"
            ],
            "filter_sky_sort": [
                "17",
                "5",
                "21",
                "9",
                "16",
                "4",
                "15",
                "14",
                "3",
                "20",
                "8",
                "13",
                "11",
                "12",
                "18",
                "6",
                "19",
                "7",
                "10",
                "2",
                "1",
                "0"
            ]
            }
        }
        },
        "focuser": {
        "focuser1": {
            "backlash": "0",
            "coef_0": "0",
            "coef_c": "0",
            "coef_date": "20300314",
            "desc": "Optec Gemini",
            "driver": "ASCOM.Simulator.Focuser",
            "has_dial_indicator": "false",
            "maximum": "12700",
            "minimum": "0",
            "name": "focuser_simulator",
            "parent": "telescope1",
            "ref_temp": "15",
            "reference": "5941",
            "step_size": "1",
            "unit": "steps",
            "unit_conversion": "0.090909090909091"
        }
        },
        "latitude": 33.3167,
        "location": "Shiquhane, Tibet,  PRC",
        "longitude": "80.0167",
        "mount": {
        "mount1": {
            "desc": "simulator mount",
            "driver": "ASCOM.Simulator.Telescope",
            "has_paddle": "false",
            "name": "mount1_alias",
            "parent": "enclosure1",
            "pointing_tel": "tel1",
            "settings": {
            "elevation_offset": "0.0",
            "home_park_altitude": "0",
            "home_park_azimuth": "174.0",
            "horizon": "20",
            "latitude_offset": "0.0",
            "longitude_offset": "0.0"
            }
        }
        },
        "name": "ALI (simulated)",
        "observatory_url": "https://www.photonranch.org/site/ALI-sim",
        "reference_ambient": [
        "5"
        ],
        "reference_pressure": [
        "839.8"
        ],
        "rotator": {
        "rotator1": {
            "backlash": "0.0",
            "desc": "Opetc Gemini",
            "driver": "ASCOM.Simulator.Rotator",
            "maximum": "360.0",
            "minimum": "-180.0",
            "name": "rotator_simulator",
            "parent": "telescope1",
            "step_size": "0.0001",
            "unit": "degree"
        }
        },
        "sequencer": {
        "sequencer": {
            "desc": "Automation Control",
            "driver": "none",
            "name": "Sequencer",
            "parent": "site"
        }
        },
        "site": "ALI-sim",
        "site_path": "Q:/",
        "telescope": {
        "telescope1": {
            "aperture": "500",
            "camera_name": "camera1",
            "collecting_area": "119773.0",
            "desc": "Planewave CDK 500 F6.8",
            "driver": "None",
            "f-ratio": "6.8",
            "filter_wheel_name": "filter_wheel1",
            "focal_length": "3454",
            "focuser_name": "focuser1",
            "has_cover": "false",
            "has_dew_heater": "false",
            "has_fans": "true",
            "name": "Main OTA",
            "obscuration": "39%",
            "parent": "mount1",
            "rotator_name": "rotator1",
            "screen_name": "screen1",
            "settings": {
            "fans": [
                "Auto",
                "High",
                "Low",
                "Off"
            ],
            "offset_collimation": "0.0",
            "offset_declination": "0.0",
            "offset_flexure": "0.0"
            }
        }
        },
        "timezone": "Asia/Kashgar"
    },
)

def testPutConfig(site, config):

    url = f"https://api.photonranch.org/test/{site}/config"
    response = requests.put(url, config)
    print(response)

def testDeleteConfig(site):
    url = f"https://api.photonranch.org/test/{site}/config"
    response = requests.delete(url)
    print(response)


if __name__=="__main__": 
    testPutConfig("tst", config)
    testDeleteConfig("tst")