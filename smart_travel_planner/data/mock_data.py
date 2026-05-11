"""
Mock data for the Smart Travel Planner.
Each city has enough activities of each type to fill a 7-day itinerary without repetition.
"""

FLIGHTS = [
    # ── ROME ──────────────────────────────────────────────────────────────
    {"from": "Helsinki", "to": "Rome",      "airline": "Finnair",      "price": 210, "duration": "3h 20m", "flight_number": "AY1871"},
    {"from": "Helsinki", "to": "Rome",      "airline": "Ryanair",      "price": 149, "duration": "3h 35m", "flight_number": "FR4422"},
    {"from": "Helsinki", "to": "Rome",      "airline": "Lufthansa",    "price": 289, "duration": "5h 10m", "flight_number": "LH3391"},

    # ── FLORENCE ──────────────────────────────────────────────────────────
    {"from": "Helsinki", "to": "Florence",  "airline": "Finnair",      "price": 225, "duration": "3h 40m", "flight_number": "AY1903"},
    {"from": "Helsinki", "to": "Florence",  "airline": "Ryanair",      "price": 159, "duration": "3h 50m", "flight_number": "FR5510"},
    {"from": "Helsinki", "to": "Florence",  "airline": "ITA Airways",  "price": 265, "duration": "4h 05m", "flight_number": "AZ1204"},

    # ── PARIS ─────────────────────────────────────────────────────────────
    {"from": "Helsinki", "to": "Paris",     "airline": "Finnair",      "price": 199, "duration": "3h 05m", "flight_number": "AY871"},
    {"from": "Helsinki", "to": "Paris",     "airline": "Air France",   "price": 249, "duration": "3h 10m", "flight_number": "AF1173"},
    {"from": "Helsinki", "to": "Paris",     "airline": "Norwegian",    "price": 139, "duration": "3h 20m", "flight_number": "DY4001"},

    # ── BARCELONA ─────────────────────────────────────────────────────────
    {"from": "Helsinki", "to": "Barcelona", "airline": "Finnair",      "price": 219, "duration": "4h 15m", "flight_number": "AY933"},
    {"from": "Helsinki", "to": "Barcelona", "airline": "Vueling",      "price": 169, "duration": "4h 25m", "flight_number": "VY8831"},
    {"from": "Helsinki", "to": "Barcelona", "airline": "SAS",          "price": 239, "duration": "4h 30m", "flight_number": "SK2261"},
]

HOTELS = [
    # ── ROME ──────────────────────────────────────────────────────────────
    {"name": "Hotel Artemide",        "city": "Rome",      "price_per_night": 145, "rating": 4.6, "family_friendly": True,  "stars": 4, "area": "Termini"},
    {"name": "The Beehive",           "city": "Rome",      "price_per_night":  72, "rating": 4.3, "family_friendly": False, "stars": 2, "area": "Esquilino"},
    {"name": "Palazzo Manfredi",      "city": "Rome",      "price_per_night": 320, "rating": 4.8, "family_friendly": False, "stars": 5, "area": "Colosseum"},
    {"name": "Hotel Santa Maria",     "city": "Rome",      "price_per_night": 110, "rating": 4.4, "family_friendly": True,  "stars": 3, "area": "Trastevere"},

    # ── FLORENCE ──────────────────────────────────────────────────────────
    {"name": "Hotel Davanzati",       "city": "Florence",  "price_per_night": 130, "rating": 4.7, "family_friendly": True,  "stars": 3, "area": "City Centre"},
    {"name": "AdAstra",               "city": "Florence",  "price_per_night":  89, "rating": 4.2, "family_friendly": False, "stars": 3, "area": "Oltrarno"},
    {"name": "Portrait Firenze",      "city": "Florence",  "price_per_night": 450, "rating": 4.9, "family_friendly": False, "stars": 5, "area": "Arno Riverside"},
    {"name": "Hotel Perseo",          "city": "Florence",  "price_per_night":  95, "rating": 4.3, "family_friendly": True,  "stars": 3, "area": "Santa Maria Novella"},

    # ── PARIS ─────────────────────────────────────────────────────────────
    {"name": "Hôtel du Continent",    "city": "Paris",     "price_per_night": 125, "rating": 4.5, "family_friendly": True,  "stars": 3, "area": "Opéra"},
    {"name": "Generator Paris",       "city": "Paris",     "price_per_night":  68, "rating": 4.1, "family_friendly": False, "stars": 2, "area": "Canal Saint-Martin"},
    {"name": "Le Meurice",            "city": "Paris",     "price_per_night": 850, "rating": 4.9, "family_friendly": False, "stars": 5, "area": "Tuileries"},
    {"name": "Hôtel Fabric",          "city": "Paris",     "price_per_night": 155, "rating": 4.6, "family_friendly": True,  "stars": 4, "area": "Oberkampf"},

    # ── BARCELONA ─────────────────────────────────────────────────────────
    {"name": "Hotel Arts Barcelona",  "city": "Barcelona", "price_per_night": 310, "rating": 4.8, "family_friendly": True,  "stars": 5, "area": "Barceloneta"},
    {"name": "Praktik Rambla",        "city": "Barcelona", "price_per_night":  98, "rating": 4.3, "family_friendly": False, "stars": 3, "area": "Las Ramblas"},
    {"name": "Cotton House Hotel",    "city": "Barcelona", "price_per_night": 220, "rating": 4.7, "family_friendly": True,  "stars": 5, "area": "Eixample"},
    {"name": "Bairro Alto Hotel",     "city": "Barcelona", "price_per_night": 135, "rating": 4.5, "family_friendly": False, "stars": 4, "area": "Gothic Quarter"},
]

ACTIVITIES = [
    # ═══════════════════════════════════════════════════════════════
    # ROME
    # ═══════════════════════════════════════════════════════════════
    # cultural
    {"name": "Colosseum & Roman Forum Tour",      "city": "Rome", "type": "cultural",  "price": 35,  "duration": "3h", "family_friendly": True,  "description": "Guided walk through ancient amphitheatre and Forum ruins"},
    {"name": "Vatican Museums & Sistine Chapel",  "city": "Rome", "type": "cultural",  "price": 45,  "duration": "4h", "family_friendly": True,  "description": "World-class art collection culminating in Michelangelo's ceiling"},
    {"name": "Borghese Gallery",                  "city": "Rome", "type": "cultural",  "price": 25,  "duration": "2h", "family_friendly": False, "description": "Baroque sculpture and Caravaggio paintings in a hilltop villa"},
    {"name": "Capitoline Museums",                "city": "Rome", "type": "cultural",  "price": 22,  "duration": "2h", "family_friendly": True,  "description": "Oldest public museums in the world on the Capitoline Hill"},
    {"name": "Palatine Hill Sunset Walk",         "city": "Rome", "type": "cultural",  "price": 15,  "duration": "2h", "family_friendly": True,  "description": "Golden-hour views over the city from the birthplace of Rome"},
    {"name": "Castel Sant'Angelo",                "city": "Rome", "type": "cultural",  "price": 18,  "duration": "2h", "family_friendly": True,  "description": "Papal fortress with panoramic terraces over the Tiber"},
    {"name": "Ostia Antica Day Trip",             "city": "Rome", "type": "cultural",  "price": 20,  "duration": "5h", "family_friendly": True,  "description": "Ancient harbour city better preserved than Pompeii"},

    # food
    {"name": "Trastevere Street Food Tour",       "city": "Rome", "type": "food",      "price": 48,  "duration": "3h", "family_friendly": True,  "description": "Supplì, maritozzi, and Roman pizza al taglio crawl"},
    {"name": "Testaccio Market Cooking Class",    "city": "Rome", "type": "food",      "price": 75,  "duration": "4h", "family_friendly": False, "description": "Shop the market then cook cacio e pepe and tiramisu"},
    {"name": "Roman Wine & Aperitivo Evening",    "city": "Rome", "type": "food",      "price": 55,  "duration": "3h", "family_friendly": False, "description": "Frascati and Cesanese pairings in an Aventine wine bar"},
    {"name": "Gelato-Making Workshop",            "city": "Rome", "type": "food",      "price": 40,  "duration": "2h", "family_friendly": True,  "description": "Learn the science behind real artisanal gelato"},
    {"name": "Jewish Ghetto Food Walk",           "city": "Rome", "type": "food",      "price": 42,  "duration": "2h", "family_friendly": True,  "description": "Carciofi alla giudia, biscotti, and centuries of history"},

    # leisure
    {"name": "Borghese Park Bike Ride",           "city": "Rome", "type": "leisure",   "price": 18,  "duration": "2h", "family_friendly": True,  "description": "Pedal through Rome's green lung past fountains and villas"},
    {"name": "Appian Way Cycling Tour",           "city": "Rome", "type": "leisure",   "price": 30,  "duration": "4h", "family_friendly": True,  "description": "Cycle Rome's oldest road past catacombs and ancient tombs"},
    {"name": "Rooftop Spa at Grand Hotel",        "city": "Rome", "type": "leisure",   "price": 90,  "duration": "3h", "family_friendly": False, "description": "City-view pool and thermal circuits above the rooftops"},
    {"name": "Pigneto Neighbourhood Stroll",      "city": "Rome", "type": "leisure",   "price": 0,   "duration": "2h", "family_friendly": False, "description": "Rome's hipster quarter — street art, vinyl, and craft beer"},

    # ═══════════════════════════════════════════════════════════════
    # FLORENCE
    # ═══════════════════════════════════════════════════════════════
    {"name": "Uffizi Gallery Deep Dive",          "city": "Florence", "type": "cultural",  "price": 38,  "duration": "4h", "family_friendly": True,  "description": "Botticelli's Birth of Venus and Raphael masterpieces"},
    {"name": "Accademia & David Tour",            "city": "Florence", "type": "cultural",  "price": 28,  "duration": "2h", "family_friendly": True,  "description": "Michelangelo's David up close with expert commentary"},
    {"name": "Medici Chapels & San Lorenzo",      "city": "Florence", "type": "cultural",  "price": 22,  "duration": "2h", "family_friendly": True,  "description": "Opulent Medici mausoleum with Michelangelo sculptures"},
    {"name": "Duomo Cupola Climb",                "city": "Florence", "type": "cultural",  "price": 20,  "duration": "2h", "family_friendly": False, "description": "463 steps to Brunelleschi's dome for rooftop panoramas"},
    {"name": "Oltrarno Artisan Workshop Tour",    "city": "Florence", "type": "cultural",  "price": 30,  "duration": "3h", "family_friendly": True,  "description": "Leather, paper-marbling and jewellery workshops across the Arno"},
    {"name": "Bargello Sculpture Museum",         "city": "Florence", "type": "cultural",  "price": 12,  "duration": "2h", "family_friendly": True,  "description": "Donatello's David and Verrocchio bronzes in a medieval palazzo"},

    {"name": "Chianti Wine & Olive Oil Tour",     "city": "Florence", "type": "food",      "price": 85,  "duration": "6h", "family_friendly": False, "description": "Half-day drive through vineyards with cellar tastings"},
    {"name": "Central Market Pasta Class",        "city": "Florence", "type": "food",      "price": 65,  "duration": "3h", "family_friendly": True,  "description": "Hand-roll pici and tagliatelle above the Mercato Centrale"},
    {"name": "Florentine Steak Dinner",           "city": "Florence", "type": "food",      "price": 70,  "duration": "3h", "family_friendly": False, "description": "Bistecca alla Fiorentina with Brunello di Montalcino"},
    {"name": "Street Food Tour: Lampredotto",     "city": "Florence", "type": "food",      "price": 35,  "duration": "2h", "family_friendly": False, "description": "Tripe sandwiches, schiacciata, and ribollita at market stalls"},

    {"name": "Boboli Gardens Morning Walk",       "city": "Florence", "type": "leisure",   "price": 12,  "duration": "2h", "family_friendly": True,  "description": "Renaissance garden terraces above the Palazzo Pitti"},
    {"name": "Arno River Kayaking",               "city": "Florence", "type": "leisure",   "price": 40,  "duration": "2h", "family_friendly": False, "description": "Paddle past Ponte Vecchio at dawn before the crowds arrive"},
    {"name": "Fiesole Hilltop Sunset",            "city": "Florence", "type": "leisure",   "price": 5,   "duration": "3h", "family_friendly": True,  "description": "Bus up to the Etruscan hilltop for sweeping valley views"},

    # ═══════════════════════════════════════════════════════════════
    # PARIS
    # ═══════════════════════════════════════════════════════════════
    {"name": "Louvre Museum Highlights Tour",     "city": "Paris", "type": "cultural",  "price": 45,  "duration": "4h", "family_friendly": True,  "description": "Mona Lisa, Venus de Milo, and Winged Victory with a guide"},
    {"name": "Musée d'Orsay Impressionist Tour",  "city": "Paris", "type": "cultural",  "price": 38,  "duration": "3h", "family_friendly": True,  "description": "Monet, Renoir, and Van Gogh in a converted Beaux-Arts station"},
    {"name": "Sainte-Chapelle & Conciergerie",    "city": "Paris", "type": "cultural",  "price": 22,  "duration": "2h", "family_friendly": True,  "description": "Gothic stained glass and Marie Antoinette's prison cell"},
    {"name": "Pompidou Centre Modern Art",        "city": "Paris", "type": "cultural",  "price": 18,  "duration": "3h", "family_friendly": False, "description": "Warhol, Matisse, and Duchamp in Paris's inside-out landmark"},
    {"name": "Versailles Palace & Gardens",       "city": "Paris", "type": "cultural",  "price": 60,  "duration": "6h", "family_friendly": True,  "description": "Hall of Mirrors, fountains, and the Sun King's grand vision"},
    {"name": "Marais Architecture Walk",          "city": "Paris", "type": "cultural",  "price": 20,  "duration": "2h", "family_friendly": True,  "description": "Medieval mansions, the Place des Vosges, and hidden courtyards"},
    {"name": "Père Lachaise Cemetery Tour",       "city": "Paris", "type": "cultural",  "price": 15,  "duration": "2h", "family_friendly": False, "description": "Oscar Wilde, Jim Morrison, and Chopin among art-nouveau tombs"},

    {"name": "Le Marais Food & Wine Tour",        "city": "Paris", "type": "food",      "price": 65,  "duration": "3h", "family_friendly": False, "description": "Falafel, pastries, and natural wine in the trendiest arrondissement"},
    {"name": "Croissant & Bread Baking Class",    "city": "Paris", "type": "food",      "price": 80,  "duration": "4h", "family_friendly": True,  "description": "Master laminated dough with a Parisian pastry chef"},
    {"name": "Montmartre Café & Absinthe Tour",   "city": "Paris", "type": "food",      "price": 55,  "duration": "3h", "family_friendly": False, "description": "Belle Époque bistros, Picasso's former café, and la fée verte"},
    {"name": "Burgundy Wine Masterclass",         "city": "Paris", "type": "food",      "price": 70,  "duration": "3h", "family_friendly": False, "description": "Premier cru tastings led by a sommelier in a cave à vins"},
    {"name": "French Cheese & Charcuterie Board", "city": "Paris", "type": "food",      "price": 45,  "duration": "2h", "family_friendly": True,  "description": "Époisses, comté, and saucisson with market sourcing lesson"},

    {"name": "Seine River Cruise at Sunset",      "city": "Paris", "type": "leisure",   "price": 28,  "duration": "2h", "family_friendly": True,  "description": "Illuminated monuments glide by from an open-deck bateaux"},
    {"name": "Luxembourg Gardens Morning Run",    "city": "Paris", "type": "leisure",   "price": 0,   "duration": "1h", "family_friendly": True,  "description": "Lap the fountains and chestnut allées at the day's start"},
    {"name": "Canal Saint-Martin Bike Tour",      "city": "Paris", "type": "leisure",   "price": 25,  "duration": "3h", "family_friendly": True,  "description": "Vélib through hip neighbourhoods along the tree-lined canal"},
    {"name": "Hammam & Spa at Grande Mosquée",    "city": "Paris", "type": "leisure",   "price": 45,  "duration": "3h", "family_friendly": False, "description": "Turkish bath ritual inside Paris's ornate 1920s mosque"},
    {"name": "Eiffel Tower Picnic & Summit",      "city": "Paris", "type": "leisure",   "price": 32,  "duration": "3h", "family_friendly": True,  "description": "Champ de Mars picnic then a lift to the second floor at dusk"},

    # ═══════════════════════════════════════════════════════════════
    # BARCELONA
    # ═══════════════════════════════════════════════════════════════
    {"name": "Sagrada Família Guided Tour",       "city": "Barcelona", "type": "cultural",  "price": 40,  "duration": "2h", "family_friendly": True,  "description": "Gaudí's unfinished basilica — towers, nave, and symbolism"},
    {"name": "Park Güell & Gaudí Houses Walk",    "city": "Barcelona", "type": "cultural",  "price": 30,  "duration": "3h", "family_friendly": True,  "description": "Mosaic terraces, gingerbread gates, and city panoramas"},
    {"name": "Picasso Museum Tour",               "city": "Barcelona", "type": "cultural",  "price": 25,  "duration": "2h", "family_friendly": True,  "description": "Early Picasso works in five connected Gothic palaces"},
    {"name": "MNAC Romanesque Collection",        "city": "Barcelona", "type": "cultural",  "price": 20,  "duration": "2h", "family_friendly": True,  "description": "Best Romanesque art collection outside of Italy on Montjuïc"},
    {"name": "Gothic Quarter Night Walk",         "city": "Barcelona", "type": "cultural",  "price": 18,  "duration": "2h", "family_friendly": False, "description": "Roman ruins, medieval squares, and legends after dark"},
    {"name": "Montserrat Monastery Day Trip",     "city": "Barcelona", "type": "cultural",  "price": 55,  "duration": "6h", "family_friendly": True,  "description": "Rack railway to the serrated mountain and the Black Madonna"},

    {"name": "Boqueria Market & Tapas Tour",      "city": "Barcelona", "type": "food",      "price": 55,  "duration": "3h", "family_friendly": True,  "description": "Jamón, anchovies, and patatas bravas at La Boqueria stalls"},
    {"name": "Catalan Cooking Class",             "city": "Barcelona", "type": "food",      "price": 70,  "duration": "3h", "family_friendly": True,  "description": "Pa amb tomàquet, fideuà, and crema catalana from scratch"},
    {"name": "Penedès Cava & Wine Tour",          "city": "Barcelona", "type": "food",      "price": 80,  "duration": "5h", "family_friendly": False, "description": "Sparkling wine cellars 45 min from the city by train"},
    {"name": "El Born Pintxos Crawl",             "city": "Barcelona", "type": "food",      "price": 45,  "duration": "3h", "family_friendly": False, "description": "Bar-hop through El Born tasting Basque-style pintxos"},

    {"name": "Barceloneta Beach Sunrise Yoga",    "city": "Barcelona", "type": "leisure",   "price": 15,  "duration": "1h", "family_friendly": True,  "description": "Salute the sun on the Mediterranean sand with a local instructor"},
    {"name": "Sitges Day Trip by Train",          "city": "Barcelona", "type": "leisure",   "price": 12,  "duration": "5h", "family_friendly": True,  "description": "Charming coastal town 40 min south — clear water and white walls"},
    {"name": "Tibidabo Amusement Park",           "city": "Barcelona", "type": "leisure",   "price": 35,  "duration": "4h", "family_friendly": True,  "description": "Retro rides on the hilltop with panoramic views of the city"},
    {"name": "Poblenou Street Art Walk",          "city": "Barcelona", "type": "leisure",   "price": 0,   "duration": "2h", "family_friendly": False, "description": "Barcelona's former industrial quarter turned creative hub"},
]