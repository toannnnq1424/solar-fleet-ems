"""Connector readiness is separate from per-device control capability."""

PROVIDERS = [
    {
        "id": "Deye",
        "implemented": True,
        "regions": ["eu", "am", "india"],
        "fields": ["app_id", "app_secret", "identity_value", "password"],
        "identity": True,
        "discovery": "plants_devices",
        "read": "native_points",
        "write": "commissioning_required",
        "evidence": ["DEYE_API_001"],
        "url": "https://developer.deyecloud.com/",
    },
    {
        "id": "Solis",
        "implemented": True,
        "regions": ["global"],
        "fields": ["key_id", "key_secret"],
        "identity": False,
        "discovery": "plants_inverters",
        "read": "native_points",
        "write": "register_profile_required",
        "evidence": ["SOLIS_DEV_DATA_002", "SOLIS_DEV_AUTH_002"],
        "url": "https://developer.soliscloud.com/guide/data-access-user.html",
    },
    {
        "id": "SOLARMAN",
        "implemented": True,
        "regions": ["global", "cn"],
        "fields": ["app_id", "app_secret", "identity_value", "password"],
        "identity": True,
        "discovery": "plants_devices",
        "read": "native_points",
        "write": "oem_profile_required",
        "evidence": ["SOLARMAN_CLOUD_002"],
        "url": "https://doc.solarmanpv.com/en/Documentation%20and%20Quick%20Guide",
    },
    *[
        {
            "id": name,
            "implemented": False,
            "regions": [],
            "fields": [],
            "identity": False,
            "discovery": "contract_required",
            "read": "contract_required",
            "write": "commissioning_required",
            "evidence": ids,
            "url": url,
        }
        for name, ids, url in [
            ("GoodWe", ["GOODWE_API_001"], "https://community.goodwe.com/static/images/2024-08-20597794.pdf"),
            ("Sungrow", ["SUNGROW_OM_001"], "https://www.isolarcloud.com/"),
            ("Huawei", ["HUAWEI_AUTH_001"], "https://intl.fusionsolar.huawei.com/"),
            ("Growatt", ["GROWATT_OSS_001"], "https://openapi.growatt.com/"),
            ("Eybond / SmartESS", ["EYBOND_GUIDE_001"], "https://www.eybond.com/"),
            (
                "Bluesun",
                ["BLUESUN_BSM_001", "BLUESUN_COMMUNITY_002", "SOLARMAN_OSS_002"],
                "https://www.bluesunpv.com/",
            ),
        ]
    ],
]


def provider(id):
    return next((p for p in PROVIDERS if p["id"] == id), None)
