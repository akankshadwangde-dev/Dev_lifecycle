"""Sample data for demo mode: an order-to-cash project with incidents, changes and new requirements."""

ISSUES = [
    {
        "key": "INC-4471", "kind": "incident", "priority": "P2", "assignee": "S. Kumar", "source": "service desk",
        "title": "Wrong shipping condition on IDoc orders for customer group 07",
        "description": "Since 14 Oct, sales orders created through IDoc ORDERS05 for customer group 07 get "
                       "shipping condition 01 instead of 02. Orders created manually in VA01 are correct. "
                       "Defaulting is done in ZCL_SD_SHIP_COND.",
    },
    {
        "key": "INC-4480", "kind": "incident", "priority": "P3", "assignee": "S. Kumar", "source": "service desk",
        "title": "Short dump CX_SY_ZERODIVIDE in ZSD_PRICING_CHECK",
        "description": "Three short dumps in production since this morning, all for sales org 2000, "
                       "in report ZSD_PRICING_CHECK during order save.",
    },
    {
        "key": "O2C-162", "kind": "change", "priority": "Medium", "assignee": "A. Developer", "source": "jira",
        "title": "Add credit status to blocked orders report",
        "description": "Extend ZSD_R_BLOCKED_ORDERS with the credit check status so sales ops can see "
                       "why an order is blocked.",
    },
    {
        "key": "O2C-170", "kind": "new", "priority": "High", "assignee": "A. Developer", "source": "jira",
        "title": "Send confirmed orders to 3PL",
        "description": "Confirmed sales orders must reach the logistics provider within 5 minutes. "
                       "The provider accepts REST JSON. Failed calls must be retried and visible to AMS.",
    },
    {
        "key": "CRM-088", "kind": "new", "priority": "Medium", "assignee": "", "source": "jira",
        "title": "Loyalty tier on Business Partner (WebUI)",
        "description": "Show a read-only Loyalty tier field on the BP overview page in CRM WebUI, "
                       "sourced from the loyalty system.",
    },
]

RESOLVED = [
    {
        "key": "INC-3920", "kind": "incident", "title": "Shipping condition not set for customer group 05",
        "description": "Orders for customer group 05 created via EDI did not get shipping condition 03.",
        "resolution": "Root cause: customer group in VBKD is empty when the defaulting BAdI runs for EDI "
                      "orders. Fix: read KDGRP from KNVV for the order's sales area when VBKD-KDGRP is "
                      "empty. Literal replaced with constant from ZIF_SD_CONSTANTS. Transport S4DK904410.",
        "url": "",
    },
    {
        "key": "INC-4102", "kind": "incident", "title": "Zero division in pricing check for sales org 1000",
        "description": "Dump CX_SY_ZERODIVIDE in ZSD_PRICING_CHECK.",
        "resolution": "No code change. Condition record ZDIS had quantity 0 after a mass upload. "
                      "Corrected the condition record in VK12; dumps stopped. Runbook RB-07 updated.",
        "url": "",
    },
]

CONFLUENCE_PAGES = [
    {
        "ref": "CONF-1001", "space": "O2C", "updated": "2026-09-03",
        "title": "BAdI ZSD_SO_SHIP_COND - Design",
        "url": "https://confluence.example.com/display/O2C/BAdI+ZSD_SO_SHIP_COND",
        "body": "Purpose: default the shipping condition (VBAK-VSBED) on sales order creation. "
                "Implemented in class ZCL_SD_SHIP_COND, method APPLY_DEFAULT. Rule: customer group 07 "
                "(wholesale) gets shipping condition 02. The user's own entry is never overwritten. "
                "Since transport S4DK911870 the logic runs in the early order-create BAdI, which is also "
                "called for IDoc ORDERS05 inbound orders.",
    },
    {
        "ref": "CONF-1002", "space": "AMS", "updated": "2026-05-20",
        "title": "KE-031 Partner and business data empty in early sales BAdIs",
        "url": "https://confluence.example.com/display/AMS/KE-031",
        "body": "Known error. In sales order BAdIs that run early during order creation, business data "
                "(VBKD, for example customer group KDGRP) and partner data are not filled yet for orders "
                "created through IDoc or EDI. Manual VA01 orders are not affected because the user enters "
                "the header first. Workaround: read the value from customer master (KNVV) for the sales "
                "area, or move the logic to a later user exit.",
    },
    {
        "ref": "CONF-1003", "space": "O2C", "updated": "2025-11-12",
        "title": "IDoc inbound processing - do not modify",
        "url": "https://confluence.example.com/display/O2C/IDoc+inbound",
        "body": "IDOC_INPUT_ORDERS and its standard flow are protected. Do not modify or copy the function "
                "module. Put custom logic in BAdIs or user exits and make it tolerate missing data.",
    },
    {
        "ref": "CONF-1004", "space": "O2C", "updated": "2026-02-01",
        "title": "Pattern: outbound REST call with retry",
        "url": "https://confluence.example.com/display/O2C/Outbound+REST",
        "body": "Standard pattern for outbound REST interfaces. Use CL_HTTP_CLIENT via an RFC destination "
                "(SM59), never hard-coded URLs. Write each call to a queue table, process with a background "
                "job, retry with backoff up to 5 times, and log to SLG1 object ZINT. Reference "
                "implementation: ZCL_MM_3PL_GR_OUT.",
    },
    {
        "ref": "CONF-1005", "space": "DEV", "updated": "2026-10-01",
        "title": "Development standards v3",
        "url": "https://confluence.example.com/display/DEV/Standards",
        "body": "NAM-07: no literals for business values, use constants from ZIF_*_CONSTANTS. SEC-03: reports "
                "reading sales data must check authorization object V_VBAK_VKO per sales organization. "
                "DOC-01: program header names the Jira key, author and transport. Classes are FINAL unless "
                "designed for inheritance.",
    },
    {
        "ref": "CONF-1006", "space": "AMS", "updated": "2026-06-14",
        "title": "Runbook RB-07 Pricing dumps after condition uploads",
        "url": "https://confluence.example.com/display/AMS/RB-07",
        "body": "Symptom: CX_SY_ZERODIVIDE in ZSD_PRICING_CHECK. Usual cause: condition records with "
                "quantity 0 after a mass upload. Check VK13 for the sales org, correct the record in VK12, "
                "then reprocess the affected orders. No transport needed.",
    },
]

SAP_SOURCES = {
    "ZCL_SD_SHIP_COND": """CLASS zcl_sd_ship_cond DEFINITION
  PUBLIC FINAL CREATE PUBLIC.

  PUBLIC SECTION.
    METHODS apply_default
      IMPORTING is_vbak TYPE vbak
                is_vbkd TYPE vbkd
      CHANGING  cs_vbak TYPE vbak.
    METHODS get_route
      IMPORTING is_vbak         TYPE vbak
      RETURNING VALUE(rv_route) TYPE route.
ENDCLASS.

CLASS zcl_sd_ship_cond IMPLEMENTATION.

  METHOD apply_default.
    " O2C-143: shipping condition 02 for wholesale customers
    IF is_vbkd-kdgrp = '07'.
      cs_vbak-vsbed = zif_sd_constants=>c_vsbed_standard.
    ENDIF.
  ENDMETHOD.

  METHOD get_route.
    SELECT SINGLE route FROM tvro
      WHERE route = @is_vbak-vsbed
      INTO @rv_route.
  ENDMETHOD.

ENDCLASS.
""",
    "ZSD_PRICING_CHECK": """REPORT zsd_pricing_check.

FORM check_discount USING is_konv TYPE konv
                    CHANGING cv_rate TYPE p.
  cv_rate = is_konv-kwert / is_konv-kmein.
ENDFORM.
""",
    "ZSD_R_BLOCKED_ORDERS": """REPORT zsd_r_blocked_orders.

TABLES vbak.
SELECT-OPTIONS s_vkorg FOR vbak-vkorg OBLIGATORY.

START-OF-SELECTION.
  SELECT vbeln, kunnr, lifsk FROM vbak
    WHERE vkorg IN @s_vkorg AND lifsk <> @space
    INTO TABLE @DATA(lt_orders).
  cl_demo_output=>display( lt_orders ).
""",
}

WHERE_USED = {
    "ZCL_SD_SHIP_COND": [
        {"name": "ZSD_SO_SHIP_COND_IMPL", "type": "BAdI implementation",
         "description": "Sales order create/change (VA01, VA02)"},
        {"name": "ZSD_IDOC_ORDERS_EXIT", "type": "Customer exit", "description": "IDoc ORDERS05 inbound"},
        {"name": "ZSD_R_SHIP_COND_SIM", "type": "Report", "description": "Simulation report for key users"},
        {"name": "ZCL_SD_ORDER_API", "type": "Class", "description": "Web shop order API"},
    ],
    "ZSD_PRICING_CHECK": [
        {"name": "MV45AFZZ", "type": "User exit", "description": "Sales order save"},
    ],
}

OPEN_TRANSPORTS = {
    "ZCL_SD_SHIP_COND": [
        {"id": "S4DK912101", "owner": "M. Iyer", "text": "O2C-158 route determination (method GET_ROUTE)"},
    ],
}

UNIT_TESTS = {
    "ZCL_SD_SHIP_COND": ["group_07_gets_standard", "group_01_unchanged", "user_entry_kept"],
}
