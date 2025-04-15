EXAMPLE_TABLE = {
    "description": "Company XYZ Registry",
    "overview": '<h2>Confluence Documentation</h2>\n<p><a href="placeholder" target="_blank" rel="noopener">Link to documentation</a></p>',
    "tags": "REGISTRIES; REGISTRY; XYZ; CUSTOMER BASE",
    "schema": {
        "fields": [
            {
                "description": "Unique bank code provided by operations",
                "name": "bank_code",
                "type": "NUMERIC",
            },
            {
                "description": "Bank ABI code",
                "name": "bank_abi",
                "type": "STRING",
                "policyTag": "gino",
            },
            {
                "description": "SSB Code - Banking Services Company",
                "name": "bank_abi_ssb",
                "type": "STRING",
            },
            {"description": "Bank name", "name": "bank_name", "type": "STRING"},
            {
                "description": "Bank nationality code",
                "name": "bank_nation_code",
                "type": "STRING",
            },
            {
                "description": "Bank nationality",
                "name": "bank_nation",
                "type": "STRING",
            },
            {
                "description": "Head office information",
                "fields": [
                    {
                        "description": "Head office country code",
                        "name": "nation_code",
                        "type": "STRING",
                    },
                    {
                        "description": "Head office country description",
                        "name": "nation",
                        "type": "STRING",
                    },
                    {
                        "description": "Head office region code",
                        "name": "region_code",
                        "type": "NUMERIC",
                    },
                    {
                        "description": "Head office region description",
                        "name": "region",
                        "type": "STRING",
                    },
                    {
                        "description": "Head office province code",
                        "name": "province_code",
                        "type": "STRING",
                    },
                    {
                        "description": "Head office province",
                        "name": "province",
                        "type": "STRING",
                    },
                    {
                        "description": "Head office postal code",
                        "name": "postal_code",
                        "type": "STRING",
                    },
                    {
                        "description": "Head office city name",
                        "name": "city",
                        "type": "STRING",
                    },
                    {
                        "description": "Head office address",
                        "name": "address",
                        "mode": "REPEATED",
                        "type": "STRING",
                    },
                ],
                "name": "head_office",
                "type": "RECORD",
            },
        ]
    },
}
