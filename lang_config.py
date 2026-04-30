"""
Language configuration module for GMC compliance scanner.

This module provides multilingual keyword patterns for detecting and validating
ecommerce policy pages (shipping, refund, privacy, TOS) across 24 languages
relevant for global dropshipping/ecommerce.

Exports:
    LANG_SIGNATURES: Language detection signatures (10 unique words per lang)
    SHIPPING_CRITICAL: Shipping policy patterns (delivery_time, shipping_cost)
    REFUND_CRITICAL: Refund policy patterns (return_window, return_shipping_cost)
    REFUND_SECTIONS: Multilingual refund section keywords
    PRIVACY_CRITICAL: Critical privacy policy keywords
    PRIVACY_RECOMMENDED: Recommended privacy policy keywords
    TOS_KEYWORDS: Terms of Service keywords (all languages)
    PAGE_ALIASES_EXTRA: Additional page path/slug patterns for non-Western languages
    SUPPORTED_LANGS: List of all supported language codes
"""

# =============================================================================
# SUPPORTED LANGUAGES
# =============================================================================

SUPPORTED_LANGS = [
    "en", "de", "nl", "fr", "es", "it", "sv", "da",  # Original 8
    "no", "fi", "pt", "pl", "cs", "ro", "tr", "ru",  # Added European
    "ja", "ko", "zh", "ar", "id", "vi", "hu", "el",  # Added Asian/Other
]

# =============================================================================
# LANGUAGE SIGNATURES
# Unique words for content-based language detection (lowercase, 10 per lang)
# =============================================================================

LANG_SIGNATURES = {
    # English
    "en": ["the", "and", "shipping", "delivery", "return", "policy", "order", "checkout", "cart", "warranty"],
    # German
    "de": ["und", "die", "der", "versand", "lieferung", "ruckgabe", "zahlung", "bestellung", "warenkorb", "widerrufsrecht"],
    # Dutch
    "nl": ["het", "van", "een", "verzending", "retourneren", "bestelling", "betaling", "winkelwagen", "levertijd", "herroepingsrecht"],
    # French
    "fr": ["les", "des", "une", "livraison", "retour", "commande", "panier", "expedition", "remboursement", "colis"],
    # Spanish
    "es": ["los", "las", "una", "envio", "devolucion", "pedido", "compra", "gastos", "reembolso", "carrito"],
    # Italian
    "it": ["gli", "una", "delle", "spedizione", "reso", "ordine", "consegna", "rimborso", "carrello", "recesso"],
    # Swedish
    "sv": ["och", "att", "som", "leverans", "frakt", "retur", "bestallning", "vardagar", "kundvagn", "angerratt"],
    # Danish
    "da": ["og", "det", "som", "levering", "forsendelse", "returnering", "bestilling", "hverdage", "fortrydelsesret", "kurv"],
    # Norwegian
    "no": ["og", "det", "som", "levering", "frakt", "retur", "bestilling", "virkedager", "angrerett", "handlekurv"],
    # Finnish
    "fi": ["ja", "on", "tai", "toimitus", "palautus", "tilaus", "toimitusaika", "arkipaivaa", "ostoskori", "peruutusoikeus"],
    # Portuguese
    "pt": ["que", "para", "uma", "entrega", "devolucao", "envio", "frete", "prazo", "pedido", "reembolso"],
    # Polish
    "pl": ["oraz", "jest", "lub", "dostawa", "zwrot", "zamowienie", "wysylka", "dni", "koszyk", "reklamacja"],
    # Czech
    "cs": ["nebo", "jako", "jsou", "dodani", "vraceni", "objednavka", "doruceni", "pracovnich", "kosik", "reklamace"],
    # Romanian
    "ro": ["sau", "este", "pentru", "livrare", "returnare", "comanda", "transport", "zile", "ramburs", "lucratoare"],
    # Turkish
    "tr": ["ve", "bir", "icin", "teslimat", "iade", "kargo", "siparis", "ucretsiz", "gonderim", "sepet"],
    # Russian
    "ru": ["или", "для", "как", "доставка", "возврат", "заказ", "оплата", "дней", "корзина", "товар"],
    # Japanese
    "ja": ["および", "または", "について", "配送", "返品", "注文", "送料", "届け", "返金", "営業日"],
    # Korean
    "ko": ["및", "또는", "대한", "배송", "반품", "주문", "무료", "환불", "영업일", "장바구니"],
    # Chinese (Simplified)
    "zh": ["和", "或", "的", "配送", "退货", "订单", "运费", "免费", "退款", "工作日"],
    # Arabic
    "ar": ["أو", "في", "على", "الشحن", "إرجاع", "طلب", "توصيل", "مجاني", "استرداد", "أيام"],
    # Indonesian
    "id": ["dan", "atau", "untuk", "pengiriman", "pengembalian", "pesanan", "gratis", "ongkir", "hari", "keranjang"],
    # Vietnamese
    "vi": ["hoac", "cho", "cua", "giao", "hang", "tra", "mien", "phi", "ngay", "gio"],
    # Hungarian
    "hu": ["vagy", "egy", "hogy", "szallitas", "visszakuldes", "rendeles", "ingyenes", "nap", "kosar", "fizetes"],
    # Greek
    "el": ["και", "για", "του", "αποστολη", "επιστροφη", "παραγγελια", "δωρεαν", "μεταφορικα", "ημερες", "καλαθι"],
}

# =============================================================================
# SHIPPING_CRITICAL
# Patterns for shipping policy validation
# =============================================================================

SHIPPING_CRITICAL = {
    # English
    "en": {
        "delivery_time": [
            r"\b\d+[-–]\d+\s*(business\s+)?days?\b",
            r"\b\d+\s*(business\s+|working\s+)?days?\b",
            "delivery time",
            "shipping time",
            "estimated delivery",
            "business days",
            "working days",
            "arrives in",
            "dispatched within",
        ],
        "shipping_cost": [
            "free shipping",
            "free delivery",
            "shipping fee",
            "delivery fee",
            "flat rate",
            "calculated at checkout",
            r"\$\d+(\.\d{2})?\s*(shipping|delivery)",
            r"(shipping|delivery)\s*:\s*\$\d+",
            "shipping included",
        ],
    },
    # German
    "de": {
        "delivery_time": [
            r"\b\d+[-–]\d+\s*(werk)?tage?\b",
            r"\b\d+\s*werktage?\b",
            "lieferzeit",
            "versandzeit",
            "arbeitstage",
            "werktage",
            "voraussichtliche lieferung",
            "lieferung innerhalb",
            "dhl", "hermes", "dpd",
        ],
        "shipping_cost": [
            "versandkostenfrei",
            "kostenloser versand",
            "versandkosten",
            "lieferkosten",
            r"\d+([,.]\d{2})?\s*€\s*(versand|lieferung)",
            "pauschale",
            "ab einem bestellwert",
            "frei haus",
            "versand inklusive",
        ],
    },
    # Dutch
    "nl": {
        "delivery_time": [
            r"\b\d+[-–]\d+\s*werkdagen\b",
            r"\b\d+\s*werkdagen\b",
            "levertijd",
            "bezorgtijd",
            "werkdagen",
            "verwachte levering",
            "levering binnen",
            "postnl", "dhl", "dpd",
            "bezorgd binnen",
        ],
        "shipping_cost": [
            "gratis verzending",
            "gratis bezorging",
            "verzendkosten",
            "bezorgkosten",
            r"€\s*\d+([,.]\d{2})?\s*(verzending|bezorging)",
            "vast tarief",
            "vanaf een bestelling",
            "verzending inbegrepen",
            "geen verzendkosten",
        ],
    },
    # French
    "fr": {
        "delivery_time": [
            r"\b\d+[-–]\d+\s*jours?\s*(ouvrables|ouvres)?\b",
            r"\b\d+\s*jours?\s*(ouvrables|ouvres)?\b",
            "delai de livraison",
            "temps de livraison",
            "jours ouvrables",
            "jours ouvres",
            "livraison estimee",
            "expedition sous",
            "colissimo", "chronopost", "mondial relay",
        ],
        "shipping_cost": [
            "livraison gratuite",
            "frais de port gratuits",
            "frais de livraison",
            "frais de port",
            r"\d+([,.]\d{2})?\s*€\s*(livraison|port)",
            "forfait",
            "franco de port",
            "port offert",
            "livraison offerte",
        ],
    },
    # Spanish
    "es": {
        "delivery_time": [
            r"\b\d+[-–]\d+\s*dias?\s*(laborables|habiles)?\b",
            r"\b\d+\s*dias?\s*(laborables|habiles)?\b",
            "plazo de entrega",
            "tiempo de envio",
            "dias laborables",
            "dias habiles",
            "entrega estimada",
            "envio en",
            "correos", "seur", "mrw",
        ],
        "shipping_cost": [
            "envio gratis",
            "envio gratuito",
            "gastos de envio",
            "coste de envio",
            r"\d+([,.]\d{2})?\s*€\s*envio",
            "tarifa plana",
            "envio incluido",
            "portes gratis",
            "sin gastos de envio",
        ],
    },
    # Italian
    "it": {
        "delivery_time": [
            r"\b\d+[-–]\d+\s*giorni\s*(lavorativi)?\b",
            r"\b\d+\s*giorni\s*(lavorativi)?\b",
            "tempi di consegna",
            "tempo di spedizione",
            "giorni lavorativi",
            "consegna stimata",
            "spedizione entro",
            "poste italiane", "bartolini", "gls",
            "consegna prevista",
        ],
        "shipping_cost": [
            "spedizione gratuita",
            "consegna gratuita",
            "spese di spedizione",
            "costi di spedizione",
            r"\d+([,.]\d{2})?\s*€\s*spedizione",
            "tariffa fissa",
            "spedizione inclusa",
            "trasporto gratuito",
            "senza spese di spedizione",
        ],
    },
    # Swedish
    "sv": {
        "delivery_time": [
            r"\b\d+[-–]\d+\s*vardagar\b",
            r"\b\d+\s*vardagar\b",
            "leveranstid",
            "frakttid",
            "vardagar",
            "arbetsdagar",
            "beraknad leverans",
            "leverans inom",
            "postnord", "dhl", "schenker",
        ],
        "shipping_cost": [
            "fri frakt",
            "gratis frakt",
            "fraktkostnad",
            "leveranskostnad",
            r"\d+\s*kr\s*(frakt|leverans)",
            "fast pris",
            "fraktfritt",
            "frakt ingår",
            "ingen fraktkostnad",
        ],
    },
    # Danish
    "da": {
        "delivery_time": [
            r"\b\d+[-–]\d+\s*hverdage\b",
            r"\b\d+\s*hverdage\b",
            "leveringstid",
            "leverancetid",
            "hverdage",
            "arbejdsdage",
            "forventet levering",
            "levering inden",
            "postnord", "gls", "dao",
        ],
        "shipping_cost": [
            "gratis fragt",
            "fri fragt",
            "forsendelsesomkostninger",
            "fragtomkostninger",
            r"\d+\s*kr\s*(fragt|forsendelse)",
            "fast pris",
            "fragtfrit",
            "fragt inkluderet",
            "ingen forsendelsesgebyr",
        ],
    },
    # Norwegian
    "no": {
        "delivery_time": [
            r"\b\d+[-–]\d+\s*virkedager\b",
            r"\b\d+\s*virkedager\b",
            "leveringstid",
            "frakttid",
            "virkedager",
            "arbeidsdager",
            "forventet levering",
            "leveranse innen",
            "posten", "postnord", "bring",
        ],
        "shipping_cost": [
            "gratis frakt",
            "fri frakt",
            "fraktkostnad",
            "fraktgebyr",
            r"\d+\s*kr\s*frakt",
            "fast pris",
            "fraktfritt",
            "frakt inkludert",
            "ingen fraktkostnader",
        ],
    },
    # Finnish
    "fi": {
        "delivery_time": [
            r"\b\d+[-–]\d+\s*arkipäivää\b",
            r"\b\d+\s*arkipäivää\b",
            "toimitusaika",
            "lähetysaika",
            "arkipäivää",
            "työpäivää",
            "arvioitu toimitus",
            "toimitus sisällä",
            "posti", "matkahuolto", "postnord",
        ],
        "shipping_cost": [
            "ilmainen toimitus",
            "maksuton toimitus",
            "toimituskulut",
            "toimitusmaksu",
            r"\d+\s*€\s*toimitus",
            "kiinteä hinta",
            "toimitus sisältyy",
            "lähetysmaksu",
            "ei toimituskuluja",
        ],
    },
    # Portuguese
    "pt": {
        "delivery_time": [
            r"\b\d+[-–]\d+\s*dias?\s*(úteis|uteis)?\b",
            r"\b\d+\s*dias?\s*(úteis|uteis)?\b",
            "prazo de entrega",
            "tempo de entrega",
            "dias úteis",
            "dias uteis",
            "entrega estimada",
            "envio em",
            "ctt", "correios", "dhl",
        ],
        "shipping_cost": [
            "frete grátis",
            "frete gratuito",
            "portes grátis",
            "custo de envio",
            "taxas de envio",
            r"\d+([,.]\d{2})?\s*€\s*(frete|envio|portes)",
            "taxa fixa",
            "envio incluído",
            "sem custos de envio",
        ],
    },
    # Polish
    "pl": {
        "delivery_time": [
            r"\b\d+[-–]\d+\s*dni\s*(roboczych)?\b",
            r"\b\d+\s*dni\s*(roboczych)?\b",
            "czas dostawy",
            "termin dostawy",
            "dni roboczych",
            "dni robocze",
            "przewidywana dostawa",
            "dostawa w ciągu",
            "poczta polska", "inpost", "dpd",
        ],
        "shipping_cost": [
            "darmowa dostawa",
            "bezpłatna wysyłka",
            "koszt wysyłki",
            "cena wysyłki",
            "koszt dostawy",
            r"\d+([,.]\d{2})?\s*(zł|pln)\s*(wysyłka|dostawa)",
            "stała opłata",
            "wysyłka w cenie",
            "bez kosztów wysyłki",
        ],
    },
    # Czech
    "cs": {
        "delivery_time": [
            r"\b\d+[-–]\d+\s*pracovních\s*dnů\b",
            r"\b\d+\s*pracovních\s*dnů\b",
            "doba doručení",
            "čas doručení",
            "pracovní dny",
            "pracovních dnů",
            "odhadované doručení",
            "dodání do",
            "česká pošta", "zásilkovna", "ppl",
        ],
        "shipping_cost": [
            "doprava zdarma",
            "doručení zdarma",
            "náklady na dopravu",
            "poštovné",
            "cena dopravy",
            r"\d+\s*kč\s*(doprava|poštovné)",
            "paušální sazba",
            "doprava v ceně",
            "bez poštovného",
        ],
    },
    # Romanian
    "ro": {
        "delivery_time": [
            r"\b\d+[-–]\d+\s*zile\s*(lucrătoare|lucratoare)?\b",
            r"\b\d+\s*zile\s*(lucrătoare|lucratoare)?\b",
            "termen de livrare",
            "timp de livrare",
            "zile lucrătoare",
            "zile lucratoare",
            "livrare estimată",
            "livrare în",
            "fan courier", "cargus", "posta romana",
        ],
        "shipping_cost": [
            "transport gratuit",
            "livrare gratuită",
            "livrare gratuita",
            "costuri de livrare",
            "taxa de transport",
            r"\d+([,.]\d{2})?\s*(lei|ron)\s*(transport|livrare)",
            "tarif fix",
            "transport inclus",
            "fără costuri de livrare",
        ],
    },
    # Turkish
    "tr": {
        "delivery_time": [
            r"\b\d+[-–]\d+\s*iş\s*günü\b",
            r"\b\d+\s*iş\s*günü\b",
            "teslimat süresi",
            "kargo süresi",
            "iş günü",
            "iş günleri",
            "tahmini teslimat",
            "teslimat içinde",
            "yurtiçi kargo", "aras", "mng",
        ],
        "shipping_cost": [
            "ücretsiz kargo",
            "ücretsiz gönderim",
            "kargo bedava",
            "kargo ücreti",
            "gönderim ücreti",
            r"\d+([,.]\d{2})?\s*(tl|₺)\s*kargo",
            "sabit ücret",
            "kargo dahil",
            "kargo ücretsiz",
        ],
    },
    # Russian
    "ru": {
        "delivery_time": [
            r"\b\d+[-–]\d+\s*рабочих\s*дней\b",
            r"\b\d+\s*рабочих\s*дней\b",
            "срок доставки",
            "время доставки",
            "рабочих дней",
            "рабочие дни",
            "ориентировочная доставка",
            "доставка за",
            "почта россии", "сдэк", "boxberry",
        ],
        "shipping_cost": [
            "бесплатная доставка",
            "доставка бесплатно",
            "стоимость доставки",
            "цена доставки",
            r"\d+\s*(руб|₽)\s*доставка",
            "фиксированная ставка",
            "доставка включена",
            "платная доставка",
            "без оплаты доставки",
        ],
    },
    # Japanese
    "ja": {
        "delivery_time": [
            r"\d+[-～]\d+\s*営業日",
            r"\d+\s*営業日",
            "配送時間",
            "お届け日数",
            "営業日",
            "配達予定",
            "お届け予定",
            "発送目安",
            "ヤマト運輸", "佐川急便", "日本郵便",
        ],
        "shipping_cost": [
            "送料無料",
            "無料配送",
            "配送無料",
            "送料",
            "配送料",
            r"\d+円\s*(送料|配送)",
            "一律料金",
            "送料込み",
            "送料別",
        ],
    },
    # Korean
    "ko": {
        "delivery_time": [
            r"\d+[-~]\d+\s*영업일",
            r"\d+\s*영업일",
            "배송 시간",
            "배송시간",
            "영업일",
            "배달 예정",
            "예상 도착",
            "발송 예정",
            "cj대한통운", "롯데택배", "한진택배",
        ],
        "shipping_cost": [
            "무료 배송",
            "무료배송",
            "무료 배달",
            "배송비",
            "배송료",
            r"\d+원\s*(배송|배달)",
            "고정 요금",
            "배송비 포함",
            "배송비 무료",
        ],
    },
    # Chinese (Simplified)
    "zh": {
        "delivery_time": [
            r"\d+[-~]\d+\s*个?工作日",
            r"\d+\s*个?工作日",
            "配送时间",
            "送货时间",
            "工作日",
            "预计到达",
            "发货时间",
            "预计送达",
            "顺丰", "圆通", "中通",
        ],
        "shipping_cost": [
            "免费送货",
            "免运费",
            "包邮",
            "运费",
            "配送费",
            r"\d+元\s*(运费|配送)",
            "统一运费",
            "运费包含",
            "免邮费",
        ],
    },
    # Arabic
    "ar": {
        "delivery_time": [
            r"\d+[-–]\d+\s*أيام?\s*(عمل)?",
            r"\d+\s*أيام?\s*(عمل)?",
            "وقت التسليم",
            "مدة الشحن",
            "أيام عمل",
            "موعد التسليم",
            "التسليم المتوقع",
            "الشحن خلال",
            "أرامكس", "سمسا", "فيديكس",
        ],
        "shipping_cost": [
            "شحن مجاني",
            "توصيل مجاني",
            "تكلفة الشحن",
            "رسوم الشحن",
            "رسوم التوصيل",
            r"\d+\s*(ريال|درهم)\s*(شحن|توصيل)",
            "سعر ثابت",
            "الشحن مشمول",
            "بدون رسوم شحن",
        ],
    },
    # Indonesian
    "id": {
        "delivery_time": [
            r"\d+[-–]\d+\s*hari\s*(kerja)?",
            r"\d+\s*hari\s*(kerja)?",
            "waktu pengiriman",
            "durasi pengiriman",
            "hari kerja",
            "estimasi pengiriman",
            "perkiraan tiba",
            "dikirim dalam",
            "jne", "j&t", "sicepat",
        ],
        "shipping_cost": [
            "gratis ongkir",
            "pengiriman gratis",
            "free ongkir",
            "biaya pengiriman",
            "ongkos kirim",
            r"rp\.?\s*\d+[.,]?\d*\s*(ongkir|pengiriman)",
            "tarif tetap",
            "ongkir sudah termasuk",
            "tanpa biaya kirim",
        ],
    },
    # Vietnamese
    "vi": {
        "delivery_time": [
            r"\d+[-–]\d+\s*ngày\s*(làm việc)?",
            r"\d+\s*ngày\s*(làm việc)?",
            "thời gian giao hàng",
            "thời gian vận chuyển",
            "ngày làm việc",
            "ước tính giao hàng",
            "dự kiến giao",
            "giao hàng trong",
            "giao hàng nhanh", "viettel post", "ghn",
        ],
        "shipping_cost": [
            "miễn phí vận chuyển",
            "giao hàng miễn phí",
            "free ship",
            "phí vận chuyển",
            "phí giao hàng",
            r"\d+[.,]?\d*\s*(đ|vnd)\s*(vận chuyển|giao hàng)",
            "phí cố định",
            "đã bao gồm vận chuyển",
            "không mất phí ship",
        ],
    },
    # Hungarian
    "hu": {
        "delivery_time": [
            r"\d+[-–]\d+\s*munkanap",
            r"\d+\s*munkanap",
            "szállítási idő",
            "kézbesítési idő",
            "munkanap",
            "becsült szállítás",
            "várható kézbesítés",
            "szállítás belül",
            "magyar posta", "gls", "foxpost",
        ],
        "shipping_cost": [
            "ingyenes szállítás",
            "szállítás díjmentes",
            "ingyenes kiszállítás",
            "szállítási díj",
            "szállítási költség",
            r"\d+\s*(ft|huf)\s*szállítás",
            "fix díj",
            "szállítás az árban",
            "díjmentes házhozszállítás",
        ],
    },
    # Greek
    "el": {
        "delivery_time": [
            r"\d+[-–]\d+\s*εργάσιμες?\s*ημέρες?",
            r"\d+\s*εργάσιμες?\s*ημέρες?",
            "χρόνος παράδοσης",
            "χρόνος αποστολής",
            "εργάσιμες ημέρες",
            "εκτιμώμενη παράδοση",
            "παράδοση εντός",
            "ώρες παράδοσης",
            "ελτα", "acs", "speedex",
        ],
        "shipping_cost": [
            "δωρεάν αποστολή",
            "δωρεάν μεταφορικά",
            "χωρίς χρέωση αποστολής",
            "κόστος αποστολής",
            "έξοδα αποστολής",
            r"\d+([,.]\d{2})?\s*€\s*αποστολή",
            "σταθερή χρέωση",
            "μεταφορικά περιλαμβάνονται",
            "χωρίς μεταφορικά",
        ],
    },
}

# =============================================================================
# REFUND_CRITICAL
# Patterns for refund/return policy validation
# =============================================================================

REFUND_CRITICAL = {
    # English
    "en": {
        "return_window": [
            r"\b\d+[-–]?\s*day\s*return",
            r"return\s*within\s*\d+\s*days?",
            "money back guarantee",
            "right of withdrawal",
            "cooling off period",
            "return period",
            "refund policy",
            "returns accepted",
        ],
        "return_shipping_cost": [
            "free returns",
            "return shipping",
            "prepaid return label",
            "return at your expense",
            "we cover return shipping",
            "return postage",
            "who pays for return",
            "return costs",
        ],
    },
    # German
    "de": {
        "return_window": [
            r"\b\d+[-–]?\s*tage?\s*rückgabe",
            r"rückgabe\s*innerhalb\s*\d+\s*tagen?",
            "geld zurück garantie",
            "widerrufsrecht",
            "widerrufsfrist",
            "rückgabefrist",
            "rückgaberecht",
            "umtausch",
        ],
        "return_shipping_cost": [
            "kostenlose rücksendung",
            "rücksendekosten",
            "retourenschein",
            "auf ihre kosten",
            "rücksendung kostenlos",
            "rückporto",
            "wer trägt die rücksendekosten",
            "kosten der rücksendung",
        ],
    },
    # Dutch
    "nl": {
        "return_window": [
            r"\b\d+[-–]?\s*dagen?\s*retour",
            r"retourneren\s*binnen\s*\d+\s*dagen?",
            "niet goed geld terug",
            "herroepingsrecht",
            "bedenktijd",
            "retourperiode",
            "retourrecht",
            "ruilen",
        ],
        "return_shipping_cost": [
            "gratis retourneren",
            "retourkosten",
            "retourlabel",
            "op eigen kosten",
            "gratis retour",
            "verzendkosten retour",
            "wie betaalt retour",
            "kosten retourzending",
        ],
    },
    # French
    "fr": {
        "return_window": [
            r"\b\d+[-–]?\s*jours?\s*(de\s*)?retour",
            r"retour\s*dans\s*les?\s*\d+\s*jours?",
            "satisfait ou remboursé",
            "droit de rétractation",
            "délai de réflexion",
            "période de retour",
            "politique de retour",
            "échange",
        ],
        "return_shipping_cost": [
            "retour gratuit",
            "frais de retour",
            "étiquette de retour",
            "à vos frais",
            "retours gratuits",
            "frais de renvoi",
            "qui paie le retour",
            "coût de retour",
        ],
    },
    # Spanish
    "es": {
        "return_window": [
            r"\b\d+[-–]?\s*días?\s*(de\s*)?devolución",
            r"devolver\s*en\s*\d+\s*días?",
            "garantía de devolución",
            "derecho de desistimiento",
            "período de reflexión",
            "plazo de devolución",
            "política de devoluciones",
            "cambio",
        ],
        "return_shipping_cost": [
            "devolución gratuita",
            "gastos de devolución",
            "etiqueta de devolución",
            "a su cargo",
            "devoluciones gratis",
            "coste de envío de devolución",
            "quién paga la devolución",
            "costes de devolución",
        ],
    },
    # Italian
    "it": {
        "return_window": [
            r"\b\d+[-–]?\s*giorni\s*(di\s*)?reso",
            r"reso\s*entro\s*\d+\s*giorni",
            "soddisfatti o rimborsati",
            "diritto di recesso",
            "periodo di riflessione",
            "periodo di reso",
            "politica di reso",
            "cambio merce",
        ],
        "return_shipping_cost": [
            "reso gratuito",
            "spese di reso",
            "etichetta di reso",
            "a vostre spese",
            "resi gratuiti",
            "costo di spedizione reso",
            "chi paga il reso",
            "costi di restituzione",
        ],
    },
    # Swedish
    "sv": {
        "return_window": [
            r"\b\d+[-–]?\s*dagars?\s*retur",
            r"returnera\s*inom\s*\d+\s*dagar",
            "nöjd kund garanti",
            "ångerrätt",
            "ångerfrist",
            "returperiod",
            "returrätt",
            "öppet köp",
        ],
        "return_shipping_cost": [
            "fri retur",
            "gratis retur",
            "returkostnad",
            "returetikett",
            "på din bekostnad",
            "returporto",
            "vem betalar retur",
            "kostnad för retur",
        ],
    },
    # Danish
    "da": {
        "return_window": [
            r"\b\d+[-–]?\s*dages?\s*retur",
            r"returnere\s*inden\s*\d+\s*dage",
            "tilfredshedsgaranti",
            "fortrydelsesret",
            "fortrydelsesfrist",
            "returperiode",
            "returret",
            "bytte",
        ],
        "return_shipping_cost": [
            "gratis retur",
            "fri returnering",
            "returomkostninger",
            "returlabel",
            "for egen regning",
            "returporto",
            "hvem betaler retur",
            "omkostninger ved retur",
        ],
    },
    # Norwegian
    "no": {
        "return_window": [
            r"\b\d+[-–]?\s*dagers?\s*retur",
            r"returnere\s*innen\s*\d+\s*dager",
            "fornøyd kunde garanti",
            "angrerett",
            "angrefrist",
            "returperiode",
            "returrett",
            "åpent kjøp",
        ],
        "return_shipping_cost": [
            "gratis retur",
            "fri retur",
            "returkostnad",
            "returetikett",
            "på egen kostnad",
            "returporto",
            "hvem betaler retur",
            "kostnad for retur",
        ],
    },
    # Finnish
    "fi": {
        "return_window": [
            r"\b\d+[-–]?\s*päivän?\s*palautus",
            r"palauttaa\s*\d+\s*päivän\s*sisällä",
            "tyytyväisyystakuu",
            "peruutusoikeus",
            "peruutusaika",
            "palautusaika",
            "palautusoikeus",
            "vaihto",
        ],
        "return_shipping_cost": [
            "ilmainen palautus",
            "maksuton palautus",
            "palautuskulut",
            "palautuslipuke",
            "omalla kustannuksella",
            "palautuspostimaksu",
            "kuka maksaa palautuksen",
            "palautuksen hinta",
        ],
    },
    # Portuguese
    "pt": {
        "return_window": [
            r"\b\d+[-–]?\s*dias?\s*(de\s*)?devolução",
            r"devolver\s*em\s*\d+\s*dias?",
            "garantia de devolução",
            "direito de arrependimento",
            "período de reflexão",
            "prazo de devolução",
            "política de devolução",
            "troca",
        ],
        "return_shipping_cost": [
            "devolução gratuita",
            "devolução grátis",
            "custos de devolução",
            "etiqueta de devolução",
            "por sua conta",
            "portes de devolução",
            "quem paga a devolução",
            "custo de retorno",
        ],
    },
    # Polish
    "pl": {
        "return_window": [
            r"\b\d+[-–]?\s*dni\s*(na\s*)?zwrot",
            r"zwrot\s*w\s*ciągu\s*\d+\s*dni",
            "gwarancja zwrotu pieniędzy",
            "prawo do odstąpienia",
            "okres zwrotu",
            "prawo zwrotu",
            "polityka zwrotów",
            "wymiana",
        ],
        "return_shipping_cost": [
            "darmowy zwrot",
            "bezpłatny zwrot",
            "koszt zwrotu",
            "etykieta zwrotna",
            "na własny koszt",
            "opłata za zwrot",
            "kto płaci za zwrot",
            "koszty odesłania",
        ],
    },
    # Czech
    "cs": {
        "return_window": [
            r"\b\d+[-–]?\s*dnů?\s*(na\s*)?vrácení",
            r"vrátit\s*do\s*\d+\s*dnů",
            "garance vrácení peněz",
            "právo na odstoupení",
            "lhůta na vrácení",
            "doba na vrácení",
            "politika vrácení",
            "výměna",
        ],
        "return_shipping_cost": [
            "vrácení zdarma",
            "bezplatné vrácení",
            "náklady na vrácení",
            "štítek pro vrácení",
            "na vlastní náklady",
            "poštovné za vrácení",
            "kdo platí vrácení",
            "náklady na odeslání zpět",
        ],
    },
    # Romanian
    "ro": {
        "return_window": [
            r"\b\d+[-–]?\s*zile\s*(de\s*)?retur",
            r"retur\s*în\s*\d+\s*zile",
            "garanția banilor înapoi",
            "drept de retragere",
            "perioada de returnare",
            "termen de returnare",
            "politica de returnare",
            "schimb",
        ],
        "return_shipping_cost": [
            "retur gratuit",
            "returnare gratuită",
            "costuri de returnare",
            "etichetă de retur",
            "pe cheltuiala dvs",
            "transport retur",
            "cine plătește returnarea",
            "costul returului",
        ],
    },
    # Turkish
    "tr": {
        "return_window": [
            r"\b\d+[-–]?\s*gün\s*(içinde\s*)?iade",
            r"iade\s*\d+\s*gün\s*içinde",
            "para iade garantisi",
            "cayma hakkı",
            "iade süresi",
            "iade hakkı",
            "iade politikası",
            "değişim",
        ],
        "return_shipping_cost": [
            "ücretsiz iade",
            "bedava iade",
            "iade kargo ücreti",
            "iade etiketi",
            "masraflar size ait",
            "iade gönderim ücreti",
            "iade ücretini kim öder",
            "geri gönderim masrafı",
        ],
    },
    # Russian
    "ru": {
        "return_window": [
            r"\b\d+[-–]?\s*дней\s*(на\s*)?возврат",
            r"возврат\s*в\s*течение\s*\d+\s*дней",
            "гарантия возврата денег",
            "право на отказ",
            "срок возврата",
            "право возврата",
            "политика возврата",
            "обмен",
        ],
        "return_shipping_cost": [
            "бесплатный возврат",
            "возврат бесплатно",
            "стоимость возврата",
            "этикетка для возврата",
            "за ваш счёт",
            "стоимость обратной пересылки",
            "кто оплачивает возврат",
            "расходы на возврат",
        ],
    },
    # Japanese
    "ja": {
        "return_window": [
            r"\d+日間?\s*返品",
            r"返品\s*\d+日以内",
            "返金保証",
            "クーリングオフ",
            "返品期間",
            "返品可能期間",
            "返品ポリシー",
            "交換",
        ],
        "return_shipping_cost": [
            "返品無料",
            "無料返品",
            "返品送料",
            "返品ラベル",
            "お客様負担",
            "返送料",
            "返品送料負担",
            "返送費用",
        ],
    },
    # Korean
    "ko": {
        "return_window": [
            r"\d+일\s*(이내\s*)?반품",
            r"반품\s*\d+일\s*이내",
            "환불 보증",
            "청약철회",
            "반품 기간",
            "반품 가능 기간",
            "반품 정책",
            "교환",
        ],
        "return_shipping_cost": [
            "무료 반품",
            "반품 무료",
            "반품 배송비",
            "반품 라벨",
            "고객 부담",
            "반송 비용",
            "반품 배송료 부담",
            "회수 비용",
        ],
    },
    # Chinese (Simplified)
    "zh": {
        "return_window": [
            r"\d+天\s*退货",
            r"退货\s*\d+天内",
            "退款保证",
            "七天无理由",
            "退货期限",
            "退货时间",
            "退货政策",
            "换货",
        ],
        "return_shipping_cost": [
            "免费退货",
            "退货免运费",
            "退货运费",
            "退货标签",
            "买家承担",
            "退回运费",
            "退货邮费",
            "寄回费用",
        ],
    },
    # Arabic
    "ar": {
        "return_window": [
            r"\d+\s*يوم\s*(للإرجاع)?",
            r"إرجاع\s*خلال\s*\d+\s*يوم",
            "ضمان استرداد الأموال",
            "حق الانسحاب",
            "فترة الإرجاع",
            "مدة الإرجاع",
            "سياسة الإرجاع",
            "استبدال",
        ],
        "return_shipping_cost": [
            "إرجاع مجاني",
            "ارجاع مجاني",
            "تكلفة الإرجاع",
            "ملصق الإرجاع",
            "على نفقتك",
            "رسوم إعادة الشحن",
            "من يدفع تكلفة الإرجاع",
            "مصاريف الإرجاع",
        ],
    },
    # Indonesian
    "id": {
        "return_window": [
            r"\d+\s*hari\s*(untuk\s*)?retur",
            r"retur\s*dalam\s*\d+\s*hari",
            "garansi uang kembali",
            "hak pembatalan",
            "periode pengembalian",
            "masa retur",
            "kebijakan pengembalian",
            "tukar",
        ],
        "return_shipping_cost": [
            "retur gratis",
            "pengembalian gratis",
            "biaya retur",
            "label pengembalian",
            "biaya ditanggung pembeli",
            "ongkir pengembalian",
            "siapa yang bayar retur",
            "biaya kirim kembali",
        ],
    },
    # Vietnamese
    "vi": {
        "return_window": [
            r"\d+\s*ngày\s*(đổi\s*)?trả",
            r"trả\s*trong\s*\d+\s*ngày",
            "đảm bảo hoàn tiền",
            "quyền hủy đơn",
            "thời gian đổi trả",
            "thời hạn trả hàng",
            "chính sách đổi trả",
            "đổi hàng",
        ],
        "return_shipping_cost": [
            "đổi trả miễn phí",
            "hoàn trả miễn phí",
            "phí đổi trả",
            "nhãn gửi trả",
            "khách hàng chịu phí",
            "phí vận chuyển trả lại",
            "ai trả phí hoàn",
            "chi phí gửi lại",
        ],
    },
    # Hungarian
    "hu": {
        "return_window": [
            r"\d+\s*napos?\s*visszaküldés",
            r"visszaküldés\s*\d+\s*napon\s*belül",
            "pénzvisszafizetési garancia",
            "elállási jog",
            "visszaküldési idő",
            "visszaküldési jog",
            "visszaküldési politika",
            "csere",
        ],
        "return_shipping_cost": [
            "ingyenes visszaküldés",
            "díjmentes visszaküldés",
            "visszaküldési költség",
            "visszaküldési címke",
            "saját költségen",
            "visszaküldési postaköltség",
            "ki fizeti a visszaküldést",
            "visszaszállítási díj",
        ],
    },
    # Greek
    "el": {
        "return_window": [
            r"\d+\s*ημερών?\s*επιστροφή",
            r"επιστροφή\s*εντός\s*\d+\s*ημερών",
            "εγγύηση επιστροφής χρημάτων",
            "δικαίωμα υπαναχώρησης",
            "περίοδος επιστροφής",
            "χρόνος επιστροφής",
            "πολιτική επιστροφών",
            "ανταλλαγή",
        ],
        "return_shipping_cost": [
            "δωρεάν επιστροφή",
            "επιστροφή δωρεάν",
            "κόστος επιστροφής",
            "ετικέτα επιστροφής",
            "με δικά σας έξοδα",
            "έξοδα επιστροφής",
            "ποιος πληρώνει την επιστροφή",
            "μεταφορικά επιστροφής",
        ],
    },
}

# =============================================================================
# REFUND_SECTIONS
# Multilingual patterns for refund section detection
# =============================================================================

REFUND_SECTIONS = {
    "cancellation_period": [
        # English
        "cancellation period", "cooling off", "withdrawal period", "right to cancel",
        # German
        "widerrufsfrist", "widerrufsrecht", "widerrufsbelehrung",
        # Dutch
        "herroepingstermijn", "bedenktijd", "herroepingsrecht",
        # French
        "délai de rétractation", "droit de rétractation", "période de réflexion",
        # Spanish
        "período de desistimiento", "derecho de desistimiento", "plazo de cancelación",
        # Italian
        "periodo di recesso", "diritto di recesso", "termine di recesso",
        # Swedish
        "ångerfrist", "ångerrätt", "avbeställning",
        # Danish
        "fortrydelsesfrist", "fortrydelsesret", "aflysning",
        # Norwegian
        "angrefrist", "angrerett", "avbestilling",
        # Finnish
        "peruutusaika", "peruutusoikeus", "peruuttaminen",
        # Portuguese
        "prazo de cancelamento", "direito de arrependimento", "período de reflexão",
        # Polish
        "okres odstąpienia", "prawo do odstąpienia", "termin anulowania",
        # Czech
        "lhůta pro odstoupení", "právo na odstoupení", "doba zrušení",
        # Romanian
        "perioada de retragere", "drept de retragere", "termen de anulare",
        # Turkish
        "cayma süresi", "cayma hakkı", "iptal süresi",
        # Russian
        "срок отмены", "право на отказ", "период отзыва",
        # Japanese
        "クーリングオフ期間", "解約期間", "撤回権",
        # Korean
        "청약철회 기간", "취소 기간", "철회권",
        # Chinese
        "取消期限", "撤销权", "冷静期",
        # Arabic
        "فترة الإلغاء", "حق الانسحاب", "مهلة الإلغاء",
        # Indonesian
        "periode pembatalan", "hak pembatalan", "masa pembatalan",
        # Vietnamese
        "thời gian hủy", "quyền hủy", "thời hạn rút lui",
        # Hungarian
        "elállási idő", "elállási jog", "lemondási időszak",
        # Greek
        "περίοδος ακύρωσης", "δικαίωμα υπαναχώρησης", "προθεσμία ακύρωσης",
    ],
    "refund_method": [
        # English
        "refund method", "how we refund", "refund to original payment", "store credit",
        # German
        "erstattungsmethode", "rückerstattung", "originalzahlungsmittel",
        # Dutch
        "terugbetalingsmethode", "hoe we terugbetalen", "oorspronkelijke betaalmethode",
        # French
        "méthode de remboursement", "mode de remboursement", "remboursement sur",
        # Spanish
        "método de reembolso", "cómo reembolsamos", "reembolso al método original",
        # Italian
        "metodo di rimborso", "come rimborsiamo", "rimborso sul metodo originale",
        # Swedish
        "återbetalningsmetod", "hur vi återbetalar", "ursprunglig betalningsmetod",
        # Danish
        "tilbagebetalingsmetode", "hvordan vi refunderer", "oprindelig betalingsmetode",
        # Norwegian
        "tilbakebetalingsmetode", "hvordan vi refunderer", "opprinnelig betalingsmetode",
        # Finnish
        "hyvitystapa", "miten hyvitämme", "alkuperäinen maksutapa",
        # Portuguese
        "método de reembolso", "como reembolsamos", "reembolso no método original",
        # Polish
        "metoda zwrotu", "jak zwracamy", "zwrot na oryginalne konto",
        # Czech
        "způsob vrácení", "jak vracíme", "vrácení na původní platební metodu",
        # Romanian
        "metoda de rambursare", "cum rambursăm", "rambursare pe metoda originală",
        # Turkish
        "iade yöntemi", "nasıl iade ediyoruz", "orijinal ödeme yöntemine iade",
        # Russian
        "способ возврата", "как мы возвращаем", "возврат на исходный способ оплаты",
        # Japanese
        "返金方法", "払い戻し方法", "元の支払い方法へ",
        # Korean
        "환불 방법", "환불 방식", "원래 결제 수단으로",
        # Chinese
        "退款方式", "如何退款", "退回原支付方式",
        # Arabic
        "طريقة الاسترداد", "كيف نقوم بالاسترداد", "استرداد إلى طريقة الدفع الأصلية",
        # Indonesian
        "metode pengembalian dana", "cara kami mengembalikan", "pengembalian ke metode pembayaran asli",
        # Vietnamese
        "phương thức hoàn tiền", "cách hoàn tiền", "hoàn về phương thức thanh toán gốc",
        # Hungarian
        "visszatérítési mód", "hogyan térítünk vissza", "eredeti fizetési módra",
        # Greek
        "μέθοδος επιστροφής χρημάτων", "πώς επιστρέφουμε", "επιστροφή στην αρχική μέθοδο πληρωμής",
    ],
    "damaged_goods": [
        # English
        "damaged goods", "defective items", "faulty products", "damaged on arrival",
        # German
        "beschädigte ware", "defekte artikel", "fehlerhafte produkte", "transportschaden",
        # Dutch
        "beschadigde goederen", "defecte artikelen", "gebrekkige producten", "beschadigd bij aankomst",
        # French
        "produits endommagés", "articles défectueux", "produits défectueux", "endommagé à la livraison",
        # Spanish
        "productos dañados", "artículos defectuosos", "productos defectuosos", "dañado al llegar",
        # Italian
        "merce danneggiata", "articoli difettosi", "prodotti difettosi", "danneggiato all'arrivo",
        # Swedish
        "skadade varor", "defekta artiklar", "felaktiga produkter", "skadad vid ankomst",
        # Danish
        "beskadigede varer", "defekte varer", "fejlbehæftede produkter", "beskadiget ved ankomst",
        # Norwegian
        "skadet varer", "defekte varer", "feilaktige produkter", "skadet ved ankomst",
        # Finnish
        "vaurioituneet tuotteet", "vialliset tuotteet", "puutteelliset tuotteet", "vaurioitunut saapuessa",
        # Portuguese
        "produtos danificados", "artigos defeituosos", "produtos com defeito", "danificado na chegada",
        # Polish
        "uszkodzone towary", "wadliwe produkty", "produkty z defektem", "uszkodzone przy dostawie",
        # Czech
        "poškozené zboží", "vadné zboží", "vadné výrobky", "poškozeno při dodání",
        # Romanian
        "produse deteriorate", "articole defecte", "produse cu defecte", "deteriorat la sosire",
        # Turkish
        "hasarlı ürünler", "kusurlu ürünler", "arızalı ürünler", "hasarlı gelen",
        # Russian
        "повреждённый товар", "бракованные товары", "дефектные изделия", "повреждён при доставке",
        # Japanese
        "破損した商品", "不良品", "欠陥商品", "到着時破損",
        # Korean
        "파손된 상품", "불량 제품", "결함 제품", "도착 시 파손",
        # Chinese
        "损坏商品", "次品", "缺陷商品", "到货破损",
        # Arabic
        "بضائع تالفة", "منتجات معيبة", "سلع معطوبة", "تالف عند الوصول",
        # Indonesian
        "barang rusak", "produk cacat", "barang bermasalah", "rusak saat tiba",
        # Vietnamese
        "hàng bị hư", "sản phẩm lỗi", "hàng khuyết tật", "bị hỏng khi đến",
        # Hungarian
        "sérült áruk", "hibás termékek", "hibás áruk", "sérült megérkezéskor",
        # Greek
        "κατεστραμμένα προϊόντα", "ελαττωματικά είδη", "ελαττωματικά προϊόντα", "κατεστραμμένο κατά την άφιξη",
    ],
    "return_procedure": [
        # English
        "return procedure", "how to return", "return instructions", "return process",
        # German
        "rückgabeverfahren", "wie man zurückgibt", "rückgabeanleitung", "rücksendeprozess",
        # Dutch
        "retourprocedure", "hoe te retourneren", "retourinstructies", "retourproces",
        # French
        "procédure de retour", "comment retourner", "instructions de retour", "processus de retour",
        # Spanish
        "procedimiento de devolución", "cómo devolver", "instrucciones de devolución", "proceso de devolución",
        # Italian
        "procedura di reso", "come restituire", "istruzioni per il reso", "processo di reso",
        # Swedish
        "returprocedur", "hur man returnerar", "returinstruktioner", "returprocess",
        # Danish
        "returprocedure", "hvordan man returnerer", "returinstruktioner", "returproces",
        # Norwegian
        "returprosedyre", "hvordan returnere", "returinstruksjoner", "returprosess",
        # Finnish
        "palautusprosessi", "kuinka palauttaa", "palautusohjeet", "palautusmenettely",
        # Portuguese
        "procedimento de devolução", "como devolver", "instruções de devolução", "processo de devolução",
        # Polish
        "procedura zwrotu", "jak zwrócić", "instrukcje zwrotu", "proces zwrotu",
        # Czech
        "postup vrácení", "jak vrátit", "pokyny k vrácení", "proces vrácení",
        # Romanian
        "procedura de returnare", "cum să returnați", "instrucțiuni de returnare", "procesul de returnare",
        # Turkish
        "iade prosedürü", "nasıl iade edilir", "iade talimatları", "iade süreci",
        # Russian
        "процедура возврата", "как вернуть", "инструкции по возврату", "процесс возврата",
        # Japanese
        "返品手続き", "返品方法", "返品の仕方", "返品プロセス",
        # Korean
        "반품 절차", "반품 방법", "반품 안내", "반품 과정",
        # Chinese
        "退货流程", "如何退货", "退货指南", "退货步骤",
        # Arabic
        "إجراءات الإرجاع", "كيفية الإرجاع", "تعليمات الإرجاع", "عملية الإرجاع",
        # Indonesian
        "prosedur pengembalian", "cara mengembalikan", "instruksi pengembalian", "proses pengembalian",
        # Vietnamese
        "thủ tục trả hàng", "cách trả hàng", "hướng dẫn trả hàng", "quy trình trả hàng",
        # Hungarian
        "visszaküldési eljárás", "hogyan küldjem vissza", "visszaküldési útmutató", "visszaküldési folyamat",
        # Greek
        "διαδικασία επιστροφής", "πώς να επιστρέψετε", "οδηγίες επιστροφής", "διαδικασία επιστροφής",
    ],
    "shipping_costs": [
        # English
        "shipping costs", "delivery charges", "postage fees", "who pays shipping",
        # German
        "versandkosten", "liefergebühren", "portokosten", "wer zahlt versand",
        # Dutch
        "verzendkosten", "leveringskosten", "portokosten", "wie betaalt verzending",
        # French
        "frais de port", "frais de livraison", "frais postaux", "qui paie les frais",
        # Spanish
        "gastos de envío", "cargos de entrega", "franqueo", "quién paga el envío",
        # Italian
        "spese di spedizione", "costi di consegna", "spese postali", "chi paga la spedizione",
        # Swedish
        "fraktkostnader", "leveranskostnader", "portokostnader", "vem betalar frakt",
        # Danish
        "forsendelsesomkostninger", "leveringsgebyrer", "portoudgifter", "hvem betaler fragt",
        # Norwegian
        "fraktkostnader", "leveringsgebyrer", "portokostnader", "hvem betaler frakt",
        # Finnish
        "toimituskulut", "toimitusmaksut", "postikulut", "kuka maksaa toimituksen",
        # Portuguese
        "custos de envio", "taxas de entrega", "custos de correio", "quem paga o envio",
        # Polish
        "koszty wysyłki", "opłaty za dostawę", "koszty przesyłki", "kto płaci za wysyłkę",
        # Czech
        "náklady na dopravu", "poplatky za doručení", "poštovné", "kdo platí dopravu",
        # Romanian
        "costuri de livrare", "taxe de livrare", "costuri poștale", "cine plătește livrarea",
        # Turkish
        "kargo ücreti", "teslimat ücreti", "posta ücreti", "kargoyu kim öder",
        # Russian
        "стоимость доставки", "плата за доставку", "почтовые расходы", "кто платит за доставку",
        # Japanese
        "送料", "配送料", "郵便料金", "送料負担",
        # Korean
        "배송비", "배달 요금", "우편 요금", "배송비 부담",
        # Chinese
        "运费", "配送费用", "邮费", "谁承担运费",
        # Arabic
        "تكاليف الشحن", "رسوم التوصيل", "رسوم البريد", "من يدفع الشحن",
        # Indonesian
        "biaya pengiriman", "biaya ongkir", "biaya pos", "siapa yang bayar ongkir",
        # Vietnamese
        "phí vận chuyển", "phí giao hàng", "phí bưu điện", "ai trả phí vận chuyển",
        # Hungarian
        "szállítási költségek", "kézbesítési díjak", "postaköltség", "ki fizeti a szállítást",
        # Greek
        "κόστος αποστολής", "χρεώσεις παράδοσης", "ταχυδρομικά", "ποιος πληρώνει τα μεταφορικά",
    ],
}

# =============================================================================
# PRIVACY_CRITICAL
# Critical privacy policy keywords per language
# =============================================================================

PRIVACY_CRITICAL = {
    "en": ["personal data", "data protection", "privacy policy", "data controller"],
    "de": ["personenbezogene daten", "datenschutz", "datenschutzerklärung", "verantwortlicher"],
    "nl": ["persoonsgegevens", "gegevensbescherming", "privacybeleid", "verwerkingsverantwoordelijke"],
    "fr": ["données personnelles", "protection des données", "politique de confidentialité", "responsable du traitement"],
    "es": ["datos personales", "protección de datos", "política de privacidad", "responsable del tratamiento"],
    "it": ["dati personali", "protezione dei dati", "informativa sulla privacy", "titolare del trattamento"],
    "sv": ["personuppgifter", "dataskydd", "integritetspolicy", "personuppgiftsansvarig"],
    "da": ["personoplysninger", "databeskyttelse", "privatlivspolitik", "dataansvarlig"],
    "no": ["personopplysninger", "personvern", "personvernerklæring", "behandlingsansvarlig"],
    "fi": ["henkilötiedot", "tietosuoja", "tietosuojaseloste", "rekisterinpitäjä"],
    "pt": ["dados pessoais", "proteção de dados", "política de privacidade", "responsável pelo tratamento"],
    "pl": ["dane osobowe", "ochrona danych", "polityka prywatności", "administrator danych"],
    "cs": ["osobní údaje", "ochrana údajů", "zásady ochrany soukromí", "správce údajů"],
    "ro": ["date personale", "protecția datelor", "politica de confidențialitate", "operator de date"],
    "tr": ["kişisel veriler", "veri koruma", "gizlilik politikası", "veri sorumlusu"],
    "ru": ["персональные данные", "защита данных", "политика конфиденциальности", "оператор данных"],
    "ja": ["個人情報", "データ保護", "プライバシーポリシー", "個人情報取扱事業者"],
    "ko": ["개인정보", "데이터 보호", "개인정보처리방침", "개인정보관리책임자"],
    "zh": ["个人信息", "数据保护", "隐私政策", "数据控制者"],
    "ar": ["البيانات الشخصية", "حماية البيانات", "سياسة الخصوصية", "مسؤول البيانات"],
    "id": ["data pribadi", "perlindungan data", "kebijakan privasi", "pengontrol data"],
    "vi": ["dữ liệu cá nhân", "bảo vệ dữ liệu", "chính sách bảo mật", "bên kiểm soát dữ liệu"],
    "hu": ["személyes adatok", "adatvédelem", "adatvédelmi irányelvek", "adatkezelő"],
    "el": ["προσωπικά δεδομένα", "προστασία δεδομένων", "πολιτική απορρήτου", "υπεύθυνος επεξεργασίας"],
}

# =============================================================================
# PRIVACY_RECOMMENDED
# Recommended privacy policy keywords per language
# =============================================================================

PRIVACY_RECOMMENDED = {
    "en": ["cookies", "third parties", "data retention", "your rights"],
    "de": ["cookies", "dritte", "speicherdauer", "ihre rechte"],
    "nl": ["cookies", "derden", "bewaartermijn", "uw rechten"],
    "fr": ["cookies", "tiers", "durée de conservation", "vos droits"],
    "es": ["cookies", "terceros", "periodo de retención", "sus derechos"],
    "it": ["cookie", "terze parti", "periodo di conservazione", "i tuoi diritti"],
    "sv": ["cookies", "tredje part", "lagringstid", "dina rättigheter"],
    "da": ["cookies", "tredjeparter", "opbevaringsperiode", "dine rettigheder"],
    "no": ["cookies", "tredjeparter", "lagringsperiode", "dine rettigheter"],
    "fi": ["evästeet", "kolmannet osapuolet", "säilytysaika", "oikeutesi"],
    "pt": ["cookies", "terceiros", "período de retenção", "seus direitos"],
    "pl": ["pliki cookie", "strony trzecie", "okres przechowywania", "twoje prawa"],
    "cs": ["soubory cookie", "třetí strany", "doba uchování", "vaše práva"],
    "ro": ["cookie-uri", "terți", "perioada de păstrare", "drepturile dvs"],
    "tr": ["çerezler", "üçüncü taraflar", "saklama süresi", "haklarınız"],
    "ru": ["куки", "третьи лица", "срок хранения", "ваши права"],
    "ja": ["クッキー", "第三者", "保存期間", "あなたの権利"],
    "ko": ["쿠키", "제3자", "보유 기간", "귀하의 권리"],
    "zh": ["cookies", "第三方", "保留期限", "您的权利"],
    "ar": ["ملفات تعريف الارتباط", "أطراف ثالثة", "فترة الاحتفاظ", "حقوقك"],
    "id": ["cookie", "pihak ketiga", "periode penyimpanan", "hak anda"],
    "vi": ["cookie", "bên thứ ba", "thời gian lưu trữ", "quyền của bạn"],
    "hu": ["sütik", "harmadik felek", "megőrzési időszak", "az ön jogai"],
    "el": ["cookies", "τρίτα μέρη", "περίοδος διατήρησης", "τα δικαιώματά σας"],
}

# =============================================================================
# TOS_KEYWORDS
# Terms of Service keywords across all languages
# =============================================================================

TOS_KEYWORDS = [
    # English
    "terms of service", "terms and conditions", "terms of use", "user agreement",
    "service agreement", "legal terms", "conditions of use", "terms & conditions",
    # German
    "allgemeine geschäftsbedingungen", "agb", "nutzungsbedingungen", "geschäftsbedingungen",
    "servicebedingungen", "nutzungsvereinbarung", "vertragsbedingungen",
    # Dutch
    "algemene voorwaarden", "gebruiksvoorwaarden", "servicevoorwaarden",
    "voorwaarden", "gebruikersovereenkomst",
    # French
    "conditions générales", "conditions d'utilisation", "conditions de service",
    "cgv", "cgu", "mentions légales", "conditions générales de vente",
    # Spanish
    "términos y condiciones", "condiciones de uso", "términos de servicio",
    "condiciones generales", "aviso legal", "condiciones de contratación",
    # Italian
    "termini e condizioni", "condizioni d'uso", "termini di servizio",
    "condizioni generali", "note legali", "condizioni di vendita",
    # Swedish
    "allmänna villkor", "användarvillkor", "tjänstevillkor",
    "villkor", "köpvillkor", "avtalsvillkor",
    # Danish
    "handelsbetingelser", "vilkår og betingelser", "brugervilkår",
    "servicevilkår", "forretningsbetingelser", "købevilkår",
    # Norwegian
    "vilkår og betingelser", "bruksvilkår", "tjenestevilkår",
    "kjøpsvilkår", "generelle vilkår", "brukervilkår",
    # Finnish
    "käyttöehdot", "palveluehdot", "yleiset ehdot",
    "tilausehdot", "sopimusehdot", "toimitusehdot",
    # Portuguese
    "termos e condições", "termos de serviço", "condições de uso",
    "condições gerais", "termos de uso", "termos e condicoes",
    # Polish
    "regulamin", "warunki użytkowania", "warunki korzystania",
    "warunki usługi", "ogólne warunki", "umowa użytkowania",
    # Czech
    "obchodní podmínky", "podmínky použití", "smluvní podmínky",
    "podmínky služby", "všeobecné podmínky", "uživatelské podmínky",
    # Romanian
    "termeni și condiții", "termeni de utilizare", "condiții de utilizare",
    "condiții generale", "termeni de serviciu", "termeni si conditii",
    # Turkish
    "kullanım koşulları", "hizmet şartları", "şartlar ve koşullar",
    "genel şartlar", "satış sözleşmesi", "kullanici sözleşmesi",
    # Russian
    "условия использования", "пользовательское соглашение", "условия обслуживания",
    "общие условия", "договор оферта", "правила использования",
    # Japanese
    "利用規約", "サービス規約", "利用条件",
    "ご利用規約", "会員規約", "取引条件",
    # Korean
    "이용약관", "서비스 이용약관", "이용 조건",
    "서비스 약관", "사용 약관", "약관",
    # Chinese
    "服务条款", "使用条款", "用户协议",
    "服务协议", "使用条件", "条款和条件",
    # Arabic
    "شروط الخدمة", "شروط الاستخدام", "الشروط والأحكام",
    "اتفاقية الاستخدام", "الشروط العامة", "شروط وأحكام",
    # Indonesian
    "syarat dan ketentuan", "ketentuan penggunaan", "ketentuan layanan",
    "syarat penggunaan", "perjanjian pengguna", "perjanjian layanan",
    # Vietnamese
    "điều khoản dịch vụ", "điều khoản sử dụng", "điều kiện sử dụng",
    "điều khoản và điều kiện", "thỏa thuận người dùng", "quy định sử dụng",
    # Hungarian
    "felhasználási feltételek", "általános szerződési feltételek", "ászf",
    "szolgáltatási feltételek", "használati feltételek", "feltételek",
    # Greek
    "όροι χρήσης", "όροι υπηρεσίας", "γενικοί όροι",
    "όροι και προϋποθέσεις", "συμφωνία χρήστη", "νομικοί όροι",
]

# =============================================================================
# PAGE_ALIASES_EXTRA
# Additional page path patterns for non-Western languages
# =============================================================================

PAGE_ALIASES_EXTRA = {
    "about": {
        "paths": [
            "/sobre", "/o-nas", "/o-firme", "/despre", "/hakkimizda",
            "/o-kompanii", "/о-компании", "/about-us",
        ],
        "slug_keywords": [
            "sobre", "onas", "ofirme", "despre", "hakkimizda", "okompanii",
            "会社概要", "会社情報", "关于我们", "关于", "소개", "회사소개",
            "من-نحن", "حول", "tentang", "gioi-thieu", "rolunk", "σχετικα",
        ],
        "title_keywords": [
            "sobre nós", "o nas", "o firmě", "despre noi", "hakkımızda",
            "о компании", "会社について", "会社概要", "关于我们", "회사 소개",
            "من نحن", "tentang kami", "về chúng tôi", "rólunk", "σχετικά με εμάς",
        ],
        "link_text": [
            "sobre", "o nas", "o nás", "despre noi", "hakkımızda",
            "о нас", "会社概要", "关于我们", "소개", "من نحن",
            "tentang kami", "về chúng tôi", "rólunk", "σχετικά",
        ],
    },
    "shipping": {
        "paths": [
            "/envio", "/entrega", "/wysylka", "/doruceni", "/livrare",
            "/kargo", "/teslimat", "/dostavka", "/доставка",
        ],
        "slug_keywords": [
            "envio", "entrega", "wysylka", "doruceni", "livrare", "kargo",
            "配送", "发货", "배송", "الشحن", "pengiriman", "giaohang",
            "szallitas", "αποστολη",
        ],
        "title_keywords": [
            "envio", "entrega", "wysyłka", "doručení", "livrare", "kargo",
            "配送について", "发货说明", "배송 안내", "الشحن والتوصيل",
            "pengiriman", "giao hàng", "szállítás", "αποστολή",
        ],
        "link_text": [
            "envío", "wysyłka", "doručení", "livrare", "kargo",
            "配送", "发货", "배송", "الشحن", "pengiriman",
            "giao hàng", "szállítás", "αποστολή",
        ],
    },
    "refund": {
        "paths": [
            "/devolucao", "/zwroty", "/vraceni", "/returnare", "/iade",
            "/vozvrat", "/возврат",
        ],
        "slug_keywords": [
            "devolucao", "zwroty", "vraceni", "returnare", "iade",
            "返品", "退货", "반품", "الإرجاع", "pengembalian", "doitra",
            "visszakuldes", "επιστροφες",
        ],
        "title_keywords": [
            "devolução", "zwroty", "vrácení", "returnare", "iade",
            "返品について", "退货政策", "반품 정책", "سياسة الإرجاع",
            "pengembalian", "đổi trả", "visszaküldés", "επιστροφές",
        ],
        "link_text": [
            "devolução", "zwroty", "vrácení", "retur", "iade",
            "返品", "退货", "반품", "إرجاع", "retur",
            "đổi trả", "visszaküldés", "επιστροφή",
        ],
    },
    "tos": {
        "paths": [
            "/termos", "/regulamin", "/podminky", "/termeni", "/kosullar",
            "/soglashenie", "/соглашение",
        ],
        "slug_keywords": [
            "termos", "regulamin", "podminky", "termeni", "kosullar",
            "利用規約", "条款", "이용약관", "الشروط", "syarat", "dieukhoan",
            "aszf", "oroi",
        ],
        "title_keywords": [
            "termos e condições", "regulamin", "podmínky", "termeni și condiții", "koşullar",
            "利用規約", "服务条款", "이용약관", "الشروط والأحكام",
            "syarat dan ketentuan", "điều khoản", "ászf", "όροι χρήσης",
        ],
        "link_text": [
            "termos", "regulamin", "podmínky", "termeni", "koşullar",
            "利用規約", "条款", "약관", "الشروط", "syarat",
            "điều khoản", "ászf", "όροι",
        ],
    },
    "privacy": {
        "paths": [
            "/privacidade", "/prywatnosc", "/soukromi", "/confidentialitate",
            "/gizlilik", "/konfidentsialnost", "/конфиденциальность",
        ],
        "slug_keywords": [
            "privacidade", "prywatnosc", "soukromi", "confidentialitate", "gizlilik",
            "プライバシー", "隐私", "개인정보", "الخصوصية", "privasi", "baomat",
            "adatvedelem", "απορρητο",
        ],
        "title_keywords": [
            "política de privacidade", "polityka prywatności", "zásady ochrany soukromí",
            "politica de confidențialitate", "gizlilik politikası",
            "プライバシーポリシー", "隐私政策", "개인정보처리방침", "سياسة الخصوصية",
            "kebijakan privasi", "chính sách bảo mật", "adatvédelem", "πολιτική απορρήτου",
        ],
        "link_text": [
            "privacidade", "prywatność", "soukromí", "confidențialitate", "gizlilik",
            "プライバシー", "隐私", "개인정보", "الخصوصية", "privasi",
            "bảo mật", "adatvédelem", "απόρρητο",
        ],
    },
    "contact": {
        "paths": [
            "/contato", "/kontakt", "/contacto", "/iletisim",
            "/kontakty", "/контакты",
        ],
        "slug_keywords": [
            "contato", "kontakt", "contacto", "iletisim",
            "お問い合わせ", "联系", "연락처", "اتصل", "kontak", "lienhe",
            "kapcsolat", "επικοινωνια",
        ],
        "title_keywords": [
            "entre em contato", "kontakt", "contacto", "iletişim",
            "お問い合わせ", "联系我们", "연락처", "اتصل بنا",
            "hubungi kami", "liên hệ", "kapcsolat", "επικοινωνία",
        ],
        "link_text": [
            "contato", "kontakt", "contacto", "iletişim",
            "連絡", "联系", "연락", "اتصال", "kontak",
            "liên hệ", "kapcsolat", "επικοινωνία",
        ],
    },
    "faq": {
        "paths": [
            "/perguntas", "/pytania", "/otazky", "/intrebari", "/sorular",
            "/voprosy", "/вопросы",
        ],
        "slug_keywords": [
            "perguntas", "pytania", "otazky", "intrebari", "sorular",
            "よくある質問", "常见问题", "자주묻는질문", "الأسئلة", "pertanyaan", "cauhoi",
            "gyik", "συχνες",
        ],
        "title_keywords": [
            "perguntas frequentes", "często zadawane pytania", "často kladené otázky",
            "întrebări frecvente", "sık sorulan sorular",
            "よくある質問", "常见问题", "자주 묻는 질문", "الأسئلة الشائعة",
            "pertanyaan umum", "câu hỏi thường gặp", "gyik", "συχνές ερωτήσεις",
        ],
        "link_text": [
            "perguntas", "pytania", "otázky", "întrebări", "sorular",
            "質問", "问题", "질문", "أسئلة", "pertanyaan",
            "câu hỏi", "kérdések", "ερωτήσεις",
        ],
    },
}
