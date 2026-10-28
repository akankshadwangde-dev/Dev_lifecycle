"""Canned model answers for the "demo" provider, so the whole flow runs without an AI model."""

import json
import re

SHIP_COND_FIXED = """CLASS zcl_sd_ship_cond DEFINITION
  PUBLIC FINAL CREATE PUBLIC.

  PUBLIC SECTION.
    METHODS apply_default
      IMPORTING is_vbak TYPE vbak
                is_vbkd TYPE vbkd
      CHANGING  cs_vbak TYPE vbak.
    METHODS get_route
      IMPORTING is_vbak         TYPE vbak
      RETURNING VALUE(rv_route) TYPE route.
  PRIVATE SECTION.
    METHODS get_customer_group
      IMPORTING is_vbak         TYPE vbak
                is_vbkd         TYPE vbkd
      RETURNING VALUE(rv_kdgrp) TYPE kdgrp.
ENDCLASS.

CLASS zcl_sd_ship_cond IMPLEMENTATION.

  METHOD apply_default.
    " O2C-143: shipping condition 02 for wholesale customers
    " INC-4471: KDGRP can be empty for IDoc orders at this point (KE-031)
    IF get_customer_group( is_vbak = is_vbak
                           is_vbkd = is_vbkd ) = zif_sd_constants=>c_kdgrp_wholesale.
      cs_vbak-vsbed = zif_sd_constants=>c_vsbed_standard.
    ENDIF.
  ENDMETHOD.

  METHOD get_route.
    SELECT SINGLE route FROM tvro
      WHERE route = @is_vbak-vsbed
      INTO @rv_route.
  ENDMETHOD.

  METHOD get_customer_group.
    rv_kdgrp = is_vbkd-kdgrp.
    IF rv_kdgrp IS NOT INITIAL.
      RETURN.
    ENDIF.
    SELECT SINGLE kdgrp FROM knvv
      WHERE kunnr = @is_vbak-kunnr
        AND vkorg = @is_vbak-vkorg
        AND vtweg = @is_vbak-vtweg
        AND spart = @is_vbak-spart
      INTO @rv_kdgrp.
  ENDMETHOD.

ENDCLASS.
"""

THREEPL_NEW = """CLASS zcl_sd_3pl_order_out DEFINITION
  PUBLIC FINAL CREATE PUBLIC.

  PUBLIC SECTION.
    " O2C-170: send confirmed orders to the 3PL (pattern: CONF-1004)
    METHODS send
      IMPORTING iv_vbeln       TYPE vbeln_va
      RETURNING VALUE(rv_sent) TYPE abap_bool.
  PRIVATE SECTION.
    CONSTANTS c_destination TYPE rfcdest VALUE 'Z3PL_ORDERS'.
    METHODS build_payload
      IMPORTING iv_vbeln          TYPE vbeln_va
      RETURNING VALUE(rv_payload) TYPE string.
ENDCLASS.

CLASS zcl_sd_3pl_order_out IMPLEMENTATION.

  METHOD send.
    cl_http_client=>create_by_destination(
      EXPORTING destination = c_destination
      IMPORTING client      = DATA(lo_client) ).
    lo_client->request->set_method( if_http_request=>co_request_method_post ).
    lo_client->request->set_content_type( 'application/json' ).
    lo_client->request->set_cdata( build_payload( iv_vbeln ) ).
    lo_client->send( ).
    lo_client->receive( ).
    lo_client->response->get_status( IMPORTING code = DATA(lv_code) ).
    rv_sent = xsdbool( lv_code BETWEEN 200 AND 299 ).
    lo_client->close( ).
  ENDMETHOD.

  METHOD build_payload.
    SELECT SINGLE vbeln, kunnr, vdatu FROM vbak
      WHERE vbeln = @iv_vbeln
      INTO @DATA(ls_order).
    rv_payload = /ui2/cl_json=>serialize( data = ls_order pretty_name = /ui2/cl_json=>pretty_mode-camel_case ).
  ENDMETHOD.

ENDCLASS.
"""

ANSWERS: dict[str, dict] = {
    "INC-4471": {
        "knowledge": {
            "cause": "Transport S4DK911870 moved the shipping condition default into "
                     "ZCL_SD_SHIP_COND=>APPLY_DEFAULT. For IDoc orders this method runs before business data "
                     "is filled, so VBKD-KDGRP is still empty and the rule for customer group 07 never fires. "
                     "This is known error KE-031; INC-3920 was fixed the same way for group 05.",
            "confidence": "high",
            "needs_code": True,
            "estimate": "0.5 day",
            "steps": [
                "Reproduce in DEV with WE19 using one of the failed production IDocs.",
                "In APPLY_DEFAULT, read the customer group from KNVV when VBKD-KDGRP is empty.",
                "Replace the literal '07' with the project constant, as in the INC-3920 fix.",
                "Add a unit test for an order with empty KDGRP.",
                "Regression test: VA01 manual order, IDoc order, customer group 01.",
                "Update the BAdI design page and add this incident to the AMS space.",
            ],
            "avoid": "Do not change IDoc processing (IDOC_INPUT_ORDERS); it is a protected standard flow.",
            "sources_used": ["CONF-1001", "CONF-1002", "INC-3920", "ZCL_SD_SHIP_COND", "CONF-1003"],
        },
        "impact": {
            "risk": "low",
            "summary": "The change only adds a fallback when the customer group is empty. "
                       "Manual orders and the web shop API always have it filled, so they behave as before.",
            "notes": [
                "Transport S4DK912101 changes GET_ROUTE in the same class; move both together or in order.",
                "3 existing unit tests cover APPLY_DEFAULT; add one for the empty customer group case.",
            ],
        },
        "plan": {
            "items": [
                {"action": "modify", "object": "ZCL_SD_SHIP_COND=>APPLY_DEFAULT", "type": "CLAS",
                 "change": "Use customer group fallback; constant instead of literal",
                 "basis": "KE-031, INC-3920", "estimate_h": 1},
                {"action": "new", "object": "ZCL_SD_SHIP_COND=>GET_CUSTOMER_GROUP", "type": "CLAS",
                 "change": "Read KDGRP from VBKD, else from KNVV for the sales area",
                 "basis": "INC-3920 fix pattern", "estimate_h": 1},
                {"action": "docs", "object": "Confluence: BAdI design page + AMS incident page", "type": "DOC",
                 "change": "Drafted at the end of the flow", "basis": "Page templates", "estimate_h": 0.5},
            ]
        },
        "build": {
            "objects": [{
                "name": "ZCL_SD_SHIP_COND",
                "new_source": SHIP_COND_FIXED,
                "notes": [
                    "New private method GET_CUSTOMER_GROUP with KNVV fallback (same as INC-3920).",
                    "Literal '07' replaced by ZIF_SD_CONSTANTS=>C_KDGRP_WHOLESALE. Check the constant exists.",
                ],
            }]
        },
        "document": {
            "pages": [
                {
                    "mode": "create", "space": "AMS", "parent": "Resolved incidents / 2026",
                    "title": "INC-4471 Shipping condition not defaulted for IDoc orders",
                    "labels": ["sd", "shipping-condition", "badi", "idoc", "ke-031"],
                    "sections": [
                        {"heading": "Symptom", "body": "Since 14 Oct, IDoc ORDERS05 orders for customer group 07 "
                                                       "got shipping condition 01 instead of 02. Manual orders "
                                                       "were correct."},
                        {"heading": "Root cause", "body": "APPLY_DEFAULT runs before business data (VBKD) is "
                                                          "filled for IDoc orders (known error KE-031)."},
                        {"heading": "Solution", "body": [
                            "New method GET_CUSTOMER_GROUP falls back to KNVV when VBKD-KDGRP is empty.",
                            "Literal replaced by ZIF_SD_CONSTANTS=>C_KDGRP_WHOLESALE."]},
                        {"heading": "Objects and transports", "body": [
                            "ZCL_SD_SHIP_COND; move together with or after S4DK912101."]},
                        {"heading": "How to spot this again", "body": "A sales BAdI behaves differently for IDoc "
                                                                      "orders than for VA01: check whether it "
                                                                      "reads data that is not filled yet."},
                    ],
                },
                {
                    "mode": "update", "space": "O2C", "parent": "Enhancements",
                    "title": "BAdI ZSD_SO_SHIP_COND - Design",
                    "labels": ["sd", "badi"],
                    "sections": [
                        {"heading": "Customer group fallback (new)", "body": "Customer group is read from VBKD and, "
                                                                             "if empty (IDoc inbound), from KNVV "
                                                                             "for the order's sales area. "
                                                                             "Introduced with INC-4471."},
                    ],
                },
            ]
        },
    },
    "INC-4480": {
        "knowledge": {
            "cause": "Same pattern as INC-4102: a condition record with quantity 0 after a mass upload makes "
                     "the division in ZSD_PRICING_CHECK fail. All dumps are for one sales org, which fits.",
            "confidence": "high",
            "needs_code": False,
            "estimate": "1 hour",
            "steps": [
                "Check condition type ZDIS for sales org 2000 in VK13 for records with quantity 0.",
                "Correct the records in VK12 (follow runbook RB-07).",
                "Reprocess the affected orders and confirm no new dumps in ST22.",
                "Optional: raise a change to guard the division in ZSD_PRICING_CHECK.",
            ],
            "avoid": "Do not transport a code fix as an emergency change; the data fix resolves the incident.",
            "sources_used": ["CONF-1006", "INC-4102", "ZSD_PRICING_CHECK"],
        },
        "document": {
            "pages": [{
                "mode": "create", "space": "AMS", "parent": "Resolved incidents / 2026",
                "title": "INC-4480 Pricing dump for sales org 2000 (data fix)",
                "labels": ["sd", "pricing", "data-fix", "rb-07"],
                "sections": [
                    {"heading": "Symptom", "body": "CX_SY_ZERODIVIDE in ZSD_PRICING_CHECK on order save, "
                                                   "sales org 2000 only."},
                    {"heading": "Root cause", "body": "Condition ZDIS records with quantity 0 after a mass upload."},
                    {"heading": "Resolution", "body": ["Corrected records in VK12 per RB-07.",
                                                       "Reprocessed affected orders. No transport."]},
                    {"heading": "How to spot this again", "body": "Pricing dumps right after a condition upload: "
                                                                  "check the uploaded records first."},
                ],
            }]
        },
    },
    "O2C-170": {
        "knowledge": {
            "cause": "New interface. Confluence has a standard pattern for outbound REST with retry and a "
                     "reference implementation (ZCL_MM_3PL_GR_OUT) that can be reused.",
            "confidence": "medium",
            "needs_code": True,
            "estimate": "4 days",
            "steps": [
                "Create RFC destination Z3PL_ORDERS in SM59 (Basis).",
                "Create ZCL_SD_3PL_ORDER_OUT following the outbound REST pattern.",
                "Trigger from order confirmation output; write each call to the queue table.",
                "Background job retries failed calls up to 5 times and logs to SLG1 object ZINT.",
                "Agree the JSON format and authentication with the 3PL (open question).",
            ],
            "avoid": "Do not hard-code the 3PL URL or credentials in ABAP.",
            "sources_used": ["CONF-1004", "CONF-1005"],
        },
        "impact": {"risk": "medium", "summary": "New objects only; no existing code changes.",
                   "notes": ["Needs an RFC destination and a background job in every system."]},
        "plan": {
            "items": [
                {"action": "new", "object": "ZCL_SD_3PL_ORDER_OUT", "type": "I",
                 "change": "Outbound REST call to the 3PL", "basis": "Pattern CONF-1004", "estimate_h": 16},
                {"action": "new", "object": "ZSD_3PL_QUEUE", "type": "I",
                 "change": "Queue table and retry job", "basis": "Pattern CONF-1004", "estimate_h": 8},
                {"action": "config", "object": "SM59 destination Z3PL_ORDERS", "type": "C",
                 "change": "Created by Basis in each system", "basis": "Pattern CONF-1004", "estimate_h": 2},
            ]
        },
        "build": {"objects": [{"name": "ZCL_SD_3PL_ORDER_OUT", "new_source": THREEPL_NEW,
                               "notes": ["Queue table and retry job not generated yet (next iteration)."]}]},
    },
}


def _generic(stage: str, title: str) -> dict:
    if stage == "knowledge":
        return {
            "cause": f"No close match in the knowledge base for '{title}'. The recommendation is based on "
                     "general SAP practice only.",
            "confidence": "low", "needs_code": True, "estimate": "unknown",
            "steps": ["Confirm the requirement details with the functional consultant.",
                      "Identify the affected objects in the system.",
                      "Draft a solution plan."],
            "avoid": "", "sources_used": [],
        }
    if stage == "impact":
        return {"risk": "medium", "summary": "No callers found in the sample data.", "notes": []}
    if stage == "plan":
        return {"items": [{"action": "new", "object": "To be decided", "type": "E", "change": title,
                           "basis": "", "estimate_h": 8}]}
    if stage == "build":
        return {"objects": []}
    if stage == "document":
        return {"pages": [{"mode": "create", "space": "O2C", "parent": "", "title": title, "labels": [],
                           "sections": [{"heading": "Summary", "body": title}]}]}
    return {}


def demo_answer(stage: str, prompt: str) -> str:
    key = re.search(r"ITEM_KEY:\s*(\S+)", prompt)
    title = re.search(r"TITLE:\s*(.+)", prompt)
    answer = ANSWERS.get(key.group(1) if key else "", {}).get(stage)
    if answer is None:
        answer = _generic(stage, title.group(1).strip() if title else "this item")
    return json.dumps(answer)
