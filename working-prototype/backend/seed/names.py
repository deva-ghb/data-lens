"""Synthetic names, drawn from regional pools so given and family names belong together.

Names are drawn at random and never influence any other generated value.
"""

REGIONS: dict[str, tuple[list[str], list[str]]] = {
    "nepal": (
        [
            "Bikash",
            "Suman",
            "Ramesh",
            "Hari",
            "Krishna",
            "Prakash",
            "Dipak",
            "Binod",
            "Santosh",
            "Kiran",
            "Sunita",
            "Gita",
        ],
        [
            "Gurung",
            "Shrestha",
            "Tamang",
            "Rai",
            "Magar",
            "Karki",
            "Basnet",
            "Ghimire",
            "Pokharel",
            "Lama",
            "Subedi",
        ],
    ),
    "south_india": (
        [
            "Anil",
            "Suresh",
            "Rajesh",
            "Manoj",
            "Vijay",
            "Murali",
            "Karthik",
            "Naveen",
            "Pradeep",
            "Mahesh",
            "Meera",
            "Lakshmi",
        ],
        ["Nair", "Menon", "Pillai", "Iyer", "Reddy", "Rao", "Varghese", "Kumar", "Thomas"],
    ),
    "north_india_pakistan": (
        [
            "Rahul",
            "Sandeep",
            "Vikram",
            "Imran",
            "Tariq",
            "Bilal",
            "Asif",
            "Sajid",
            "Zubair",
            "Faisal",
            "Deepak",
            "Ankit",
        ],
        [
            "Sharma",
            "Singh",
            "Verma",
            "Yadav",
            "Khan",
            "Malik",
            "Qureshi",
            "Iqbal",
            "Shah",
            "Siddiqui",
            "Mishra",
        ],
    ),
    "bangladesh": (
        ["Farhan", "Arif", "Kamal", "Jamal", "Hamid", "Rafiq", "Nadia", "Shirin"],
        ["Rahman", "Hossain", "Islam", "Uddin", "Chowdhury", "Alam", "Akhtar"],
    ),
    "sri_lanka": (
        ["Nimal", "Chandra", "Lakshman", "Ruwan", "Kumari"],
        ["Perera", "Fernando", "DeSilva", "Silva", "Jayasinghe"],
    ),
    "philippines": (
        ["Jose", "Mark", "Rafael", "Noel", "Edwin", "Ramon", "Ana", "Maria", "Rosa", "Grace"],
        ["Santos", "Reyes", "Cruz", "Ramos", "Mendoza", "Garcia", "Torres", "Lopez", "Bautista"],
    ),
    "east_africa": (
        ["Moses", "John", "Simon", "Peter", "Isaac", "Samuel", "Esther"],
        ["Kamau", "Mwangi", "Otieno", "Njoroge", "Wanjiru", "Ochieng"],
    ),
    "west_africa": (
        ["Kofi", "Kwame", "Tunde", "Adebayo", "Emmanuel", "Elijah", "Ama"],
        ["Mensah", "Asante", "Osei", "Adeyemi", "Okafor", "Okoro", "Boateng"],
    ),
    "arab": (
        [
            "Ahmad",
            "Omar",
            "Saeed",
            "Yusuf",
            "Nabil",
            "Samir",
            "Hassan",
            "Ibrahim",
            "Mariam",
            "Leila",
            "Yasmin",
            "Noor",
        ],
        ["Haddad", "Nasser", "Saleh", "Jaber", "Mahmoud", "Yousef", "Abdullah", "Aziz", "Habib"],
    ),
}

REGION_WEIGHTS = {
    "nepal": 0.2,
    "south_india": 0.18,
    "north_india_pakistan": 0.18,
    "bangladesh": 0.12,
    "sri_lanka": 0.05,
    "philippines": 0.1,
    "east_africa": 0.06,
    "west_africa": 0.05,
    "arab": 0.06,
}

# Display language preferences (a screen setting only, never a model input).
DISPLAY_LANGUAGES = ["en", "en", "en", "ar", "hi", "ur", "ne", "bn", "ml", "tl", "ta"]
