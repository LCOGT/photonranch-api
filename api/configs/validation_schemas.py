wema_config_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "observatory_id": {"type": "string"},
        "name": {"type": "string"},
        "observatory_name": {"type": "string"},
        "observatory_location": {"type": "string"},
        "observatory_latitude": {"type": "number"},
        "observatory_longitude": {"type": "number"},
        "observatory_elevation": {"type": "number"},
        "observatory_state": {"type": "string"},
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
            "additionalProperties": {"type": "number"},
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
        "name",
        "observatory_elevation",
        "observatory_id",
        "observatory_latitude",
        "observatory_location",
        "observatory_longitude",
        "observatory_name",
        "observatory_state",
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
                            "bin_enable": {
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
                            "chan_color": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "coarse_bin": {
                                "type": "array",
                                "items": {"type": "integer"}
                            },
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
                            "optimal_bin": {
                                "type": "array",
                                "items": {"type": "integer"}
                            },
                            "pix_scale": {"type": "number"},
                            "saturate": {"type": "integer"}
                        },
                        "required": [
                            "areas_implemented",
                            "area_sq_deg",
                            "bin-desc",
                            "bin_enable",
                            "bin_modes",
                            "CameraXSize",
                            "CameraYSize",
                            "can_set_gain",
                            "can_subframe",
                            "chan_color",
                            "coarse_bin",
                            "default_area",
                            "fullwell_capacity",
                            "has_chiller",
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
                            "optimal_bin",
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
                                            "items": {"type": "integer"}
                                        },
                                        {"type": "integer"},
                                        {"type": "integer"},
                                        {
                                            "type": "array",
                                            "items": {"type": "integer"}
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
                    "aperture",
                    "f-ratio",
                    "focal_length",
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
