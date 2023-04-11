wema_config_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "site_id": {"type": "string"},
        "site_description": {"type": "string"},
        "site_location": {"type": "string"},
        "site_latitude": {"type": "number"},
        "site_longitude": {"type": "number"},
        "site_elevation": {"type": "number"},
        "TZ_database_name": {"type": "string"},
        "defaults": {
            "type": "object",
            "properties": {
                "enclosure": {"type": "string"},
                "observing_conditions": {"type": "string"}
            },
            "required": ["enclosure", "observing_conditions"]
        },
        "device_types": {"type": "array"},
        "observing_conditions": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                },
                "required": ["name"]
            }
        },
        "enclosure": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "is_dome": {
                        "type": "boolean"
                    },
                    "mode": {
                        "type": "string",
                    },
                    "name": {
                        "type": "string"
                    },
                    "settings": {
                        "type": "object",
                        "properties": {
                            "lights": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                },
                                "uniqueItems": True
                            },
                            "roof_shutter": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                },
                                "uniqueItems": True
                            }
                        },
                        "required": ["lights", "roof_shutter"]
                    }
                },
                "required": ["is_dome", "mode", "name", "settings"]
            }
        },
        "events": {
            "type": "object",
            "properties": {
                "Astro Dark": {"type": "number"},
                "Civil Dawn": {"type": "number"},
                "Civil Dusk": {"type": "number"},
                "Clock & Auto Focus": {"type": "number"},
                "Close and Park": {"type": "number"},
                "Cool Down, Open": {"type": "number"},
                "End Astro Dark": {"type": "number"},
                "End Eve Bias Dark": {"type": "number"},
                "End Eve Sky Flats": {"type": "number"},
                "End Morn Bias Dark": {"type": "number"},
                "End Morn Sky Flats": {"type": "number"},
                "End Nightly Reset": {"type": "number"},
                "Eve Bias Dark": {"type": "number"},
                "Eve Sky Flats": {"type": "number"},
                "Middle of Night": {"type": "number"},
                "Moon Rise": {"type": "number"},
                "Moon Set": {"type": "number"},
                "Moon Transit": {"type": "number"},
                "Morn Bias Dark": {"type": "number"},
                "Morn Sky Flats": {"type": "number"},
                "Naut Dawn": {"type": "number"},
                "Naut Dusk": {"type": "number"},
                "Nightly Reset": {"type": "number"},
                "Observing Begins": {"type": "number"},
                "Observing Ends": {"type": "number"},
                "Ops Window Closes": {"type": "number"},
                "Ops Window Start": {"type": "number"},
                "Prior Moon Rise": {"type": "number"},
                "Prior Moon Set": {"type": "number"},
                "Prior Moon Transit": {"type": "number"},
                "Sun Rise": {"type": "number"},
                "Sun Set": {"type": "number"},
                "use_by": {"type": "number"}
            },
            "required": [
                "Astro Dark",
                "Civil Dawn",
                "Civil Dusk",    
                "Clock & Auto Focus",    
                "Close and Park",    
                "Cool Down, Open",    
                "End Astro Dark",    
                "End Eve Bias Dark",    
                "End Eve Sky Flats",    
                "End Morn Bias Dark",    
                "End Morn Sky Flats",    
                "End Nightly Reset",    
                "Eve Bias Dark",    
                "Eve Sky Flats",    
                "Middle of Night",    
                "Moon Rise",    
                "Moon Set",    
                "Moon Transit",    
                "Morn Bias Dark",    
                "Morn Sky Flats",    
                "Naut Dawn",    
                "Naut Dusk",    
                "Nightly Reset",    
                "Observing Begins",    
                "Observing Ends",    
                "Ops Window Closes",    
                "Ops Window Start",    
                "Prior Moon Rise",    
                "Prior Moon Set",    
                "Prior Moon Transit",    
                "Sun Rise",    
                "Sun Set",    
                "use_by"
            ]
        },
    },
    "required": [
        "defaults",
        "device_types",
        "enclosure",
        "events",
        "site_elevation",
        "site_id",
        "site_latitude",
        "site_location",
        "site_longitude",
        "site_description",
        "observing_conditions",
        "TZ_database_name",
    ]
}

platform_config_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "site": {"type": "string"},
        "site_id": {"type": "string"},
        "obs_id": {"type": "string"},
        "name": {"type": "string"},
        "TZ_database_name": {"type": "string"},
        "telescope_description": {"type": "string"},
        "defaults": {
            "type": "object",
            "additionalProperties": {"type": "string"},
            "required": [
                "camera",
                "filter_wheel",
                "focuser",
                "mount",
                "rotator",
                "screen",
                "telescope"
            ]
        },
        "device_types": {
            "type": "array",
            "items": {"type": "string"}
        },
        "camera": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "desc": {"type": "string"},
                    "name": {"type": "string"},
                    "parent": {"type": "string"},
                    "settings": {
                        "type": "object",
                        "properties": {
                            "areas_implemented": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "area_sq_deg": {"type": "number"},
                            "bin-desc": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "bin_modes": {
                                "type": "array",
                                "items": {
                                    "type": "array",
                                    "items": [
                                        {"type": "string"},
                                        {"type": "number"}
                                    ]
                                }
                            },
                            "CameraXSize": {"type": "integer"},
                            "CameraYSize": {"type": "integer"},
                            "can_set_gain": {"type": "boolean"},
                            "can_subframe": {"type": "boolean"},
                            "dark_exposure": {"type": "integer"},
                            "default_area": {"type": "string"},
                            "fullwell_capacity": {"type": "integer"},
                            "has_chiller": {"type": "boolean"},
                            "has_darkslide": {"type": "boolean"},
                            "has_screen": {"type": "boolean"},
                            "is_cmos": {"type": "boolean"},
                            "is_color": {"type": "boolean"},
                            "is_osc": {"type": "boolean"},
                            "max_daytime_exposure": {"type": "number"},
                            "max_exposure": {"type": "integer"},
                            "max_linearity": {"type": "integer"},
                            "min_exposure": {"type": "number"},
                            "min_subframe": {
                                "type": "array",
                                "items": {"type": "integer"}
                            },
                            "number_of_bias_to_collect": {"type": "integer"},
                            "number_of_dark_to_collect": {"type": "integer"},
                            "number_of_flat_to_collect": {"type": "integer"},
                            "pix_scale": {"type": "number"},
                            "saturate": {"type": "integer"}
                        },
                        "required": [
                            "areas_implemented",
                            "bin_modes",
                            "CameraXSize",
                            "CameraYSize",
                            "can_set_gain",
                            "can_subframe",
                            "dark_exposure",
                            "default_area",
                            "fullwell_capacity",
                            "has_darkslide",
                            "has_screen",
                            "is_cmos",
                            "is_color",
                            "is_osc",
                            "max_daytime_exposure",
                            "max_exposure",
                            "max_linearity",
                            "min_exposure",
                            "min_flat_exposure",
                            "min_subframe",
                            "number_of_bias_to_collect",
                            "number_of_dark_to_collect",
                            "number_of_flat_to_collect",
                            "pix_scale",
                            "saturate"
                        ]
                    }
                },
                "required": ["desc", "name", "parent", "settings"]
            }
        },
        "filter_wheel": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "desc": {"type": "string"},
                    "settings": {
                        "type": "object",
                        "properties": {
                            "default_filter": {"type": "string"},
                            "filter_data": {
                                "type": "array",
                                "items": {
                                    "type": "array",
                                    "items": [
                                        {"type": "string"},
                                        {
                                            "type": "array",
                                            "items": {"type": "number"}
                                        },
                                        {"type": "number"},
                                        {"type": "number"},
                                        {
                                            "type": "array",
                                            "items": {"type": "number"}
                                        },
                                        {"type": "string"}
                                    ]
                                }
                            }
                        },
                        "required": [
                            "default_filter",
                            "filter_data"
                        ]
                    }
                },
                "required": [
                    "name",
                    "settings"
                ]
            }
        },
        "focuser": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "maximum": {"type": "integer"},
                    "minimum": {"type": "integer"},
                    "step_size": {"type": "integer"},
                    "unit": {"type": "string"}
                },
                "required": [
                    "name",
                    "maximum",
                    "minimum",
                    "step_size",
                    "unit"
                ]
            }
        },
        "mount": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "alignment": {"type": "string"},
                    "pointing_tel": {"type": "string"}
                },
                "required": [
                    "name",
                    "alignment",
                    "pointing_tel"
                ]
            }
        },
        "rotator": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "minimum": {"type": "number"},
                    "maximum": {"type": "number"},
                    "step_size": {"type": "number"},
                    "unit": {"type": "string"}
                },
                "required": [
                    "name",
                    "minimum",
                    "maximum",
                    "step_size",
                    "unit"]
            }
        },
        "screen": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "minimum": {"type": "integer"},
                    "saturate": {"type": "integer"}
                },
                "required": [
                    "name",
                    "minimum",
                    "saturate"
                ]
            }
        },
        "selector": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "cameras": {
                        "type": "array",
                        "items": {"type": ["null", "string"]}
                    },
                    "guiders": {
                        "type": "array",
                        "items": {"type": ["null", "string"]}
                    },
                    "instruments": {
                        "type": "array",
                        "items": {"type": ["null", "string"]}
                    },
                },
                "required": [
                    "name",
                    "cameras",
                    "guiders",
                    "instruments",
                ]
            }
        },
        "sequencer": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                },
                "required": ["name"]
            }
        },
        "telescope": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "aperture": {"type": "integer"},
                    "camera_name": {"type": "string"},
                    "filter_wheel_name": {"type": "string"},
                    "focuser_name": {"type": "string"},
                    "rotator_name": {"type": "string"},
                    "screen_name": {"type": "string"},
                    "f-ratio": {"type": "number"},
                    "focal_length": {"type": "integer"},
                    "has_cover": {"type": "boolean"},
                    "has_fans": {"type": "boolean"},
                    "has_instrument_selector": {"type": "boolean"},
                    "selector_positions": {"type": "integer"},
                },
                "required": [
                    "name",
                    "camera_name",
                    "filter_wheel_name",
                    "rotator_name",
                    "focuser_name",
                    "screen_name",
                    "has_cover",
                    "has_fans",
                    "has_instrument_selector",
                ]
            }
        },
    },
    "required": [
        "site",
        "site_id",
        "obs_id",
        "name",
        "TZ_database_name",
        "telescope_description",
        "defaults",
        "device_types",
        "camera",
        "filter_wheel",
        "focuser",
        "mount",
        "screen",
        "telescope",
    ]
}
