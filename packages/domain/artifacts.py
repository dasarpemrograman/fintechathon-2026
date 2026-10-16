"""Controlled commercial templates bind figures to a stored scenario analysis."""


def money(value):
    return value["currency"] + " " + value["amount"] if value else "[amount unresolved]"


def schedule(value):
    if value["kind"] == "fixed":
        due = value["due"]
        return (
            (due.get("instant") or due.get("date") or "[date unresolved]")
            + " ("
            + due["timezone"]
            + ")"
        )
    return (
        value["anchor_milestone_id"]
        + " "
        + ("+" if value["offset_days"] >= 0 else "")
        + str(value["offset_days"])
        + " "
        + value["day_basis"]
        + " days"
    )


def render(deal, scenario, analysis, kind, language, recipient=None, funding=None):
    from services.api.store import DomainError

    if language not in {"id", "en"}:
        raise DomainError(
            "DRAFT_LANGUAGE_UNSUPPORTED",
            "Templates currently support Indonesian and English; choose id or en.",
        )
    placeholders = [
        "governing law",
        "dispute resolution",
        "remaining counterparty agreement",
    ]
    parties = {p["id"]: p for p in deal["parties"]}
    internal = kind in {"recommendation", "finance_pack"}
    visible = (
        set(parties)
        if internal
        else {
            p["id"]
            for p in deal["parties"]
            if "seller" in p["roles"] or (recipient is None and "buyer" in p["roles"])
        }
        | ({recipient} if recipient else set())
    )
    introductions = {
        "recommendation": (
            "Tinjauan internal: gunakan angka analisis, kekurangan kas dan bukti berikut untuk menilai usulan.",
            "Internal review: assess the proposal using the following analysis, cash needs and evidence.",
        ),
        "message": (
            "Usulan untuk ditinjau oleh pihak penerima. Mohon konfirmasikan barang, pengiriman dan jadwal pembayaran yang dinyatakan berikut.",
            "Proposal for recipient review. Please confirm the following goods, shipment scope and dated payment terms.",
        ),
        "agreement": (
            "Usulan kesepakatan komersial; setiap pihak harus meninjau ketentuan dan melengkapi bagian hukum sebelum penandatanganan.",
            "Proposed commercial agreement; each party must review terms and complete legal placeholders before signature.",
        ),
        "clause_revision": (
            "Usulan pengganti klausul [original clause reference]: gunakan ketentuan pembayaran berikut; konfirmasikan lingkup klausul yang diganti.",
            "Proposed replacement of [original clause reference]: use the following payment terms; confirm the exact clause scope.",
        ),
        "amendment": (
            "Usulan perubahan atas [original agreement reference], berlaku [amendment effective date]. Ketentuan yang diubah memerlukan penerimaan setiap pihak terkait.",
            "Proposed amendment to [original agreement reference], effective [amendment effective date]. Changed terms require each affected party's acceptance.",
        ),
        "finance_pack": (
            "Dokumen persiapan pembiayaan untuk ditinjau; bukan pengajuan atau keputusan pemberi pinjaman.",
            "Financing preparation for review; neither a submission nor a lender decision.",
        ),
    }
    if kind not in introductions:
        raise DomainError(
            "DRAFT_KIND_UNSUPPORTED", "Choose a supported controlled template."
        )
    if kind == "message" and not recipient:
        placeholders.append("recipient party")
    if kind == "clause_revision":
        placeholders.append("original clause reference")
    if kind == "amendment":
        placeholders.extend(
            ["original agreement reference", "amendment effective date"]
        )

    rows = [
        "DRAFT — not sent, signed or submitted",
        "Document: " + kind + " · requested language: " + language,
        "Scenario: " + scenario["id"],
        "Analysis: " + analysis["snapshot_hash"],
        "Evidence digest: " + analysis["evidence_digest"],
        "",
        introductions[kind][0 if language == "id" else 1],
        "Counterparties",
    ]
    for party in deal["parties"]:
        if party["id"] not in visible:
            continue
        rows.append(
            "- "
            + ", ".join(party["roles"])
            + ": "
            + (
                party["legal_name"]
                or party["display_name"] + " [legal identity unconfirmed]"
            )
        )
    if recipient:
        rows += ["Recipient: " + parties[recipient]["display_name"]]
    rows += ["", "Goods and declared quantities"]
    for line in deal["line_items"]:
        rows.append(
            "- "
            + line["product"]["description"]
            + ": "
            + line["quantity"]
            + " "
            + line["unit"]
        )
    rows += ["", "Shipment scope"]
    for shipment in deal["shipments"]:
        term = shipment.get("incoterm")
        place = shipment.get("named_place")
        rows.append(
            "- "
            + shipment["dispatch_country"]
            + " → "
            + shipment["destination_country"]
            + " · "
            + shipment["mode"]
            + " · "
            + (term or "[Incoterm]")
            + " "
            + (place or "[named place]")
        )
        if not term:
            placeholders.append("Incoterm: " + shipment["id"])
        if not place:
            placeholders.append("named place: " + shipment["id"])
    rows += ["", "Declared invoice amounts"]
    for invoice in deal["invoices"]:
        if not {invoice["payer_party_id"], invoice["payee_party_id"]} <= visible:
            continue
        rows.append(
            "- "
            + invoice["side"]
            + ": "
            + money(invoice["amount"])
            + " · "
            + invoice["id"]
        )
    rows += ["", "Proposed payment terms (counterparty acceptance is separate)"]
    for term in deal["payment_terms"]:
        if not {term["payer_id"], term["payee_id"]} <= visible:
            continue
        amount = (
            money(term["amount"])
            if term["amount"]
            else (
                term["invoice_fraction"] + " of " + term["invoice_id"]
                if term["invoice_fraction"] is not None
                else "[amount unresolved]"
            )
        )
        rows.append(
            "- "
            + parties[term["payer_id"]]["display_name"]
            + " → "
            + parties[term["payee_id"]]["display_name"]
            + ": "
            + amount
            + " · "
            + schedule(term["schedule"])
            + " · "
            + term["instrument"]
        )
    if internal:
        rows += [
            "",
            "Analysis-bound economics",
            "Planned contribution: "
            + money(analysis["after_financing"]["contribution"]),
            "Calculation completeness: " + analysis["completeness"],
        ]
        if analysis["cash_metrics"]:
            cash = analysis["cash_metrics"]
            rows += [
                "Minimum cash: "
                + cash["reporting_currency"]
                + " "
                + cash["minimum_cash"],
                "Buffer shortfall: " + cash["buffer_shortfall"],
                "Horizon: " + cash["horizon_end"],
            ]
    if funding:
        rows += [
            "",
            "Finance preparation only",
            "Requested draw: " + money(funding["draw"]),
        ]
        for event in funding["schedule"]:
            rows.append(
                "- "
                + event["kind"]
                + ": "
                + money(event["amount"])
                + " · "
                + schedule(event["schedule"])
                + " · "
                + event["status"]
            )
    rows += ["", "Legal and acceptance placeholders"] + [
        "[" + value + "]" for value in placeholders
    ]
    rows += [
        "",
        "This draft is not proof of agreement, lender approval, disbursement, booking, payment or customs filing. Review the selected scenario, current evidence and every placeholder.",
    ]
    if language == "id":
        labels = {
            "DRAFT — not sent, signed or submitted": "DRAF — belum dikirim, ditandatangani atau diajukan",
            "Counterparties": "Pihak terkait",
            "Goods and declared quantities": "Barang dan jumlah yang dinyatakan",
            "Shipment scope": "Lingkup pengiriman",
            "Declared invoice amounts": "Nilai faktur yang dinyatakan",
            "Proposed payment terms (counterparty acceptance is separate)": "Usulan ketentuan pembayaran (penerimaan pihak terkait dicatat terpisah)",
            "Analysis-bound economics": "Perhitungan yang terikat pada analisis",
            "Finance preparation only": "Persiapan pembiayaan saja",
            "Legal and acceptance placeholders": "Bagian hukum dan penerimaan yang perlu dilengkapi",
            "This draft is not proof of agreement, lender approval, disbursement, booking, payment or customs filing. Review the selected scenario, current evidence and every placeholder.": "Draf ini bukan bukti kesepakatan, persetujuan pemberi pinjaman, pencairan, pemesanan, pembayaran atau pelaporan pabean. Tinjau skenario, bukti terkini dan setiap bagian yang belum lengkap.",
        }
        prefixes = {
            "Document: ": "Dokumen: ",
            "Scenario: ": "Skenario: ",
            "Analysis: ": "Analisis: ",
            "Evidence digest: ": "Hash bukti: ",
            "Recipient: ": "Penerima: ",
            "Planned contribution: ": "Kontribusi rencana: ",
            "Calculation completeness: ": "Kelengkapan perhitungan: ",
            "Minimum cash: ": "Kas minimum: ",
            "Buffer shortfall: ": "Kekurangan penyangga: ",
            "Horizon: ": "Akhir horizon: ",
            "Requested draw: ": "Pencairan yang diminta: ",
        }
        rows = [labels.get(row, row) for row in rows]
        for index, row in enumerate(rows):
            for original, translated in prefixes.items():
                if row.startswith(original):
                    rows[index] = translated + row[len(original) :]
                    break
        # Keep technical enum values, amounts, original party/product names and
        # legal placeholders exact; they are source facts, not translated prose.
    return "\n".join(rows), placeholders
