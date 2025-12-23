from ursina import Ursina, Entity, Button, Text, camera, color, Sequence, window, mouse

# Sequence helpers (desktop Ursina)
try:
    from ursina import Wait, Func
except Exception:
    try:
        from ursina.sequence import Wait, Func
    except Exception:
        Wait = None
        Func = None

# Brython timers (Ursina CSS / browser)
HAS_BRYTHON_TIMER = False
bry_timer = None
try:
    from browser import timer as bry_timer
    HAS_BRYTHON_TIMER = True
except Exception:
    HAS_BRYTHON_TIMER = False
    bry_timer = None


# -----------------------
# Color helpers (Ursina CSS uses hsla strings)
# -----------------------
def hsv(h, s, v, a=1):
    try:
        return color.hsv(h, s, v, a)
    except TypeError:
        return color.hsv(h, s, v)
    except Exception:
        return getattr(color, 'white', 'white')


WHITE = getattr(color, 'white', hsv(0, 0, 1))
BLACK = getattr(color, 'black', hsv(0, 0, 0))
SMOKE = getattr(color, 'smoke', hsv(0, 0, 0.96))


def clamp(v, lo, hi):
    try:
        if v < lo:
            return lo
        if v > hi:
            return hi
        return v
    except Exception:
        return lo


def safe_setattr(obj, name, value):
    try:
        setattr(obj, name, value)
        return True
    except Exception:
        return False


def set_visible(obj, visible):
    """Robust show/hide across desktop + Ursina CSS."""
    if obj is None:
        return
    if hasattr(obj, 'enabled'):
        try:
            obj.enabled = visible
            return
        except Exception:
            pass
    if hasattr(obj, 'visible'):
        try:
            obj.visible = visible
            return
        except Exception:
            pass
    # fallback: scale to zero
    try:
        if visible:
            if hasattr(obj, '_saved_scale'):
                obj.scale = obj._saved_scale
        else:
            obj._saved_scale = obj.scale
            obj.scale = (0, 0)
    except Exception:
        pass


def style_button(btn, bg, fg):
    """Force readable button colors in Ursina CSS."""
    if btn is None:
        return
    safe_setattr(btn, 'color', bg)

    if hasattr(btn, 'text_entity') and btn.text_entity is not None:
        safe_setattr(btn.text_entity, 'color', fg)
    if hasattr(btn, 'text_color'):
        safe_setattr(btn, 'text_color', fg)


def _vec2_to_xy(v):
    try:
        if isinstance(v, (tuple, list)) and len(v) >= 2:
            return float(v[0]), float(v[1])
        if hasattr(v, 'x') and hasattr(v, 'y'):
            return float(v.x), float(v.y)
    except Exception:
        pass
    return None, None


def get_window_pixel_size():
    try:
        return _vec2_to_xy(getattr(window, 'size', None))
    except Exception:
        return None, None


def get_aspect_ratio():
    try:
        a = window.aspect_ratio
        if a and a > 0:
            return float(a)
    except Exception:
        pass

    w, h = get_window_pixel_size()
    try:
        if w and h:
            return float(w) / float(h)
    except Exception:
        pass

    try:
        a = camera.aspect_ratio
        if a and a > 0:
            return float(a)
    except Exception:
        pass

    return 1.0


class Layout:
    """
    - safe bounds for camera.ui (avoid clipping on mobile)
    - mobile text scaling (iOS Safari makes Text huge otherwise)
    - ui_scale shrinks the whole UI window slightly on mobile
    """
    def __init__(self):
        self.aspect = get_aspect_ratio()

        # Browser (Ursina CSS) behaves like normalized UI space.
        if HAS_BRYTHON_TIMER:
            self.half_w = 0.5
        else:
            self.half_w = 0.5 * self.aspect

        self.half_h = 0.5

        # Safe padding (avoid edges / iPhone overlays)
        self.pad_x = 0.06 if HAS_BRYTHON_TIMER else 0.03
        self.pad_top = 0.07 if HAS_BRYTHON_TIMER else 0.05
        self.pad_bottom = 0.09 if HAS_BRYTHON_TIMER else 0.05

        self.left = -self.half_w + self.pad_x
        self.right = self.half_w - self.pad_x
        self.top = self.half_h - self.pad_top
        self.bottom = -self.half_h + self.pad_bottom

        self.w = self.right - self.left
        self.h = self.top - self.bottom

        # Pixel size & "mobile" detection
        self.pw, self.ph = get_window_pixel_size()
        self.is_portrait = False
        try:
            if self.pw and self.ph:
                self.is_portrait = self.ph > self.pw
        except Exception:
            self.is_portrait = False

        # Text scaling factor (critical for iOS Safari)
        if HAS_BRYTHON_TIMER:
            if self.pw and self.ph:
                min_dim = min(self.pw, self.ph)
                tf = clamp(min_dim / 900.0, 0.35, 1.0)
                if self.is_portrait:
                    tf *= 0.92
                self.text_factor = tf
            else:
                self.text_factor = 0.60
        else:
            self.text_factor = 1.0

        self.is_narrow = (self.w < 1.15) or (self.is_portrait and HAS_BRYTHON_TIMER)

        # UI window slightly smaller on mobile
        self.ui_scale = 0.94 if HAS_BRYTHON_TIMER else 1.0


# -----------------------
# Scheduler: browser.timer in Brython, Sequence on desktop
# -----------------------
class _DesktopInterval:
    def __init__(self, callback, seconds):
        self.callback = callback
        self.seconds = seconds
        self.active = True
        self.seq = None
        self._schedule_next()

    def _schedule_next(self):
        if not self.active:
            return

        def tick():
            if not self.active:
                return
            self.callback()
            self._schedule_next()

        try:
            if Wait is not None and Func is not None:
                self.seq = Sequence(Wait(self.seconds), Func(tick))
            else:
                self.seq = Sequence(self.seconds, tick)

            if hasattr(self.seq, 'start'):
                self.seq.start()
            else:
                self.seq()
        except Exception:
            self.active = False

    def cancel(self):
        self.active = False


class _DesktopTimeout:
    def __init__(self, callback, seconds):
        self.active = True
        self.callback = callback

        def run():
            if self.active:
                self.callback()

        try:
            if Wait is not None and Func is not None:
                self.seq = Sequence(Wait(seconds), Func(run))
            else:
                self.seq = Sequence(seconds, run)

            if hasattr(self.seq, 'start'):
                self.seq.start()
            else:
                self.seq()
        except Exception:
            self.active = False

    def cancel(self):
        self.active = False


class Scheduler:
    def __init__(self):
        self.backend = 'browser.timer' if HAS_BRYTHON_TIMER else 'Sequence'

    def set_interval(self, callback, seconds):
        if HAS_BRYTHON_TIMER:
            try:
                return bry_timer.set_interval(callback, int(seconds * 1000))
            except Exception:
                return None
        return _DesktopInterval(callback, seconds)

    def clear_interval(self, handle):
        if handle is None:
            return
        if HAS_BRYTHON_TIMER:
            try:
                bry_timer.clear_interval(handle)
            except Exception:
                pass
        else:
            try:
                handle.cancel()
            except Exception:
                pass

    def set_timeout(self, callback, seconds):
        if HAS_BRYTHON_TIMER:
            try:
                return bry_timer.set_timeout(callback, int(seconds * 1000))
            except Exception:
                return None
        return _DesktopTimeout(callback, seconds)

    def clear_timeout(self, handle):
        if handle is None:
            return
        if HAS_BRYTHON_TIMER:
            try:
                bry_timer.clear_timeout(handle)
            except Exception:
                pass
        else:
            try:
                handle.cancel()
            except Exception:
                pass


# -----------------------
# Word system (no file I/O)
# -----------------------
class WordSelector:
    def __init__(self, bank):
        self.bank = bank
        self.categories = list(bank.keys())
        self.bag = []
        self.i = 0
        self.last = None
        self._rng = 123456789

    def _rand_index(self, n):
        try:
            import random
            return random.randrange(n)
        except Exception:
            self._rng = (1103515245 * self._rng + 12345) % (2 ** 31)
            return self._rng % n

    def _shuffle(self, lst):
        for k in range(len(lst) - 1, 0, -1):
            j = self._rand_index(k + 1)
            lst[k], lst[j] = lst[j], lst[k]

    def set_categories(self, cats):
        self.categories = list(cats) if cats else list(self.bank.keys())
        self.bag = []
        for c in self.categories:
            self.bag += self.bank.get(c, [])
        if not self.bag:
            self.bag = ['(No words selected)']
        self._shuffle(self.bag)
        self.i = 0
        self.last = None

    def next_word(self):
        if not self.bag:
            return '(No words)'
        if self.i >= len(self.bag):
            self._shuffle(self.bag)
            self.i = 0
        w = self.bag[self.i]
        self.i += 1

        if w == self.last and len(self.bag) > 1:
            if self.i >= len(self.bag):
                self._shuffle(self.bag)
                self.i = 0
            w2 = self.bag[self.i]
            self.i += 1
            self.bag[self.i - 1] = w
            w = w2

        self.last = w
        return w


# -----------------------
# Main app controller
# -----------------------
class CharadesApp:
    STATE_MENU = 'menu'
    STATE_SETUP = 'setup'
    STATE_SETTINGS = 'settings'
    STATE_HOWTO = 'howto'
    STATE_GAMEPLAY = 'gameplay'
    STATE_SUMMARY = 'summary'
    STATE_FINAL = 'final'

    PHASE_REVEAL = 'reveal'
    PHASE_COUNTDOWN = 'countdown'
    PHASE_PLAYING = 'playing'
    PHASE_PAUSED = 'paused'

    def __init__(self):
        self.scheduler = Scheduler()
        self.layout = Layout()

        # Theme
        self.C_BG = hsv(230, 0.35, 0.12)
        self.C_PANEL = hsv(230, 0.28, 0.18)
        self.C_PANEL2 = hsv(230, 0.25, 0.25)

        self.C_STRIPE1 = hsv(260, 0.50, 0.18)
        self.C_STRIPE2 = hsv(190, 0.55, 0.18)
        self.C_STRIPE3 = hsv(330, 0.45, 0.18)

        self.C_BTN_DARK = hsv(230, 0.18, 0.28)
        self.C_PRIMARY = hsv(210, 1.00, 0.90)
        self.C_GOOD = hsv(120, 1.00, 0.90)
        self.C_WARN = hsv(45,  1.00, 0.95)
        self.C_BAD = hsv(340, 1.00, 0.95)

        self.team_colors = [
            hsv(0,   1.00, 0.95),
            hsv(210, 1.00, 0.95),
            hsv(120, 1.00, 0.90),
            hsv(270, 1.00, 0.95),
        ]

        # Settings
        self.pass_penalty = 0
        self.auto_next_word = True

        # Language
        self.language = 'en'  # 'en' or 'de'
        self._de = {
            "Pantomime / Charades (2D)": "Pantomime / Scharaden (2D)",

            "Play": "Spielen",
            "Settings": "Einstellungen",
            "How To Play": "Spielanleitung",
            "Quit": "Beenden",
            "Back": "Zurück",

            "Pass penalty: OFF (0)": "Pass-Strafe: AUS (0)",
            "Pass penalty: ON (-1)": "Pass-Strafe: AN (-1)",
            "Auto-next word: ON": "Auto-nächstes Wort: AN",
            "Auto-next word: OFF": "Auto-nächstes Wort: AUS",

            "Round time": "Rundenzeit",
            "Rounds / team": "Runden / Team",
            "Categories (multi-select)": "Kategorien (Mehrfachauswahl)",
            "Categories": "Kategorien",
            "Start Game": "Spiel starten",

            "(Word hidden)": "(Wort versteckt)",

            ".Only the actor should see\n.Tap Reveal Word":
                ".Nur der Darsteller darf sehen\n.Tippe auf Wort zeigen",
            ".Tap Reveal Word when only the actor can see":
                ".Tippe auf Wort zeigen, wenn nur der Darsteller es sehen kann",

            "Reveal Word": "Wort zeigen",
            "Correct (+1)": "Richtig (+1)",
            "End Round": "Runde beenden",

            "SCORES": "PUNKTE",

            "Paused": "Pausiert",
            "Resume": "Weiter",
            "Back to Menu": "Zurück zum Menü",

            "Correct! +1": "Richtig! +1",
            "(Tap Next Word)": "(Tippe Nächstes Wort)",
            "Next Word": "Nächstes Wort",
            "Pass": "Passen",
            "Pass (-1)": "Passen (-1)",

            "Round Summary": "Rundenübersicht",
            "Next Turn": "Nächster Zug",
            "Menu": "Menü",

            "Final Results": "Endergebnis",
            "Restart": "Neu starten",

            "Timer backend failed — use End Round.":
                "Timer-Backend fehlgeschlagen — nutze Runde beenden.",

            ".Browser: close the tab to quit\n.Desktop: close the window to quit":
                ".Browser: Tab schließen zum Beenden\n.Desktop: Fenster schließen zum Beenden",

            # Keep the ursina_css ".Line ..." format exactly
            ".One player acts the word silently •\n"
            ".Teammates guess •\n"
            ".Tap Reveal Word → 3…2…1 → timer starts •\n"
            ".Correct = +1 point •\n"
            ".Pass = 0 or -1 (Settings) •\n"
            ".End Round ends early •\n"
            ".Teams rotate turns. Highest score wins •":
                ".Ein Spieler stellt das Wort stumm dar •\n"
                ".Teamkollegen raten •\n"
                ".Tippe auf Wort zeigen → 3…2…1 → Timer startet •\n"
                ".Richtig = +1 Punkt •\n"
                ".Passen = 0 oder -1 (Einstellungen) •\n"
                ".Runde beenden beendet früh •\n"
                ".Teams wechseln sich ab. Höchste Punktzahl gewinnt •",
        }

        # Setup defaults
        self.num_teams = 2
        self.round_duration = 60
        self.rounds_per_team = 3

        # Word bank
        self.word_bank = self._make_word_bank()
        self.word_bank_de = self._make_word_bank_de()

        # Category filter:
        # empty set means "ALL categories"
        self.selected_categories = set()

        self.selector = WordSelector(self.word_bank)
        self.selector.set_categories(list(self.selected_categories))

        # Game state
        self.state = None
        self.phase = None
        self.phase_before_pause = None
        self.turn_index = 0
        self.scores = []
        self.round_points = 0
        self.time_left = 0
        self.current_word = ''
        self.waiting_for_next = False
        self.paused = False

        # Timer handles
        self._round_interval = None
        self._countdown_interval = None
        self._flash_timeout = None

        # UI roots
        self.root = None
        self.bg_root = None
        self.ui_root = None

        # UI refs
        self.header_score_text = None
        self.timer_text = None
        self.timer_bar_bg = None
        self.timer_bar_fill = None
        self.word_text = None
        self.message_text = None
        self.countdown_text = None

        self.btn_word_action = None
        self.btn_correct = None
        self.btn_pass = None
        self.btn_end = None
        self.btn_pause = None

        self.score_panel = None
        self.score_title = None
        self.score_texts = []
        self.score_rows = []

        self.pause_overlay = None
        self.pause_panel = None
        self.pause_label = None
        self.pause_btn_resume = None
        self.pause_btn_menu = None

        safe_setattr(window, 'title', 'Charades (2D)')
        safe_setattr(window, 'color', self.C_BG)

        self.go(self.STATE_MENU)

    def _tf(self):
        try:
            return float(self.layout.text_factor)
        except Exception:
            return 1.0

    def _tr(self, text):
        # Always return a string when possible
        try:
            s = str(text)
        except Exception:
            return text

        if getattr(self, 'language', 'en') != 'de':
            return s

        d = getattr(self, '_de', None)
        if isinstance(d, dict) and s in d:
            return d[s]

        # Dynamic/pattern translations
        if s.startswith("Timer backend: "):
            return "Timer-Backend: " + s[len("Timer backend: "):]

        if s.startswith("Winner: "):
            return s.replace("Winner: ", "Sieger: ", 1)

        if s.startswith("Tie: "):
            return s.replace("Tie: ", "Unentschieden: ", 1)

        if s.startswith("Team ") and " gained: " in s:
            return s.replace(" gained: ", " erhielt: ", 1)

        if s.startswith("Pass ("):
            return "Passen" + s[len("Pass"):]

        if " • " in s and "Round" in s:
            return s.replace("Round", "Runde")

        if s.startswith("Startup error:"):
            return s.replace("Startup error:", "Startfehler:", 1)

        return s

    def _active_word_bank(self):
        """Return the word bank matching the current UI language."""
        if getattr(self, 'language', 'en') == 'de':
            b = getattr(self, 'word_bank_de', None)
            if isinstance(b, dict) and b:
                return b
        return getattr(self, 'word_bank', {})

    def _make_word_bank(self):
        return {
            "Classic": [
                "air guitar", "banana peel", "campfire", "snowball fight", "birthday party",
                "brain freeze", "elevator", "juggling", "pirate", "ghost",
                "zombie walk", "hula hoop", "ice skating", "spaghetti slurp", "walking on stilts",
                "clown", "cowboy", "dinosaur", "fireworks", "tickle monster",
                "pillow fight", "paper airplane", "kite flying", "opening a gift", "high five",
            ],
            "Cringe": [
                "reply-all disaster", "mic unmuted", "camera on in pajamas", "autocorrect fail", "awkward high five",
                "influencer apology", "buffering video", "typing then disappearing", "accidental pocket call", "wrong group chat",
                "saying you too", "double text", "forgetting someones name", "bad pun", "dad dance",
                "laughing at your own joke", "spilling coffee", "voice crack", "wave at wrong person", "holding the door too long",
                "trip on nothing", "zoom filter glitch", "posting then deleting", "reading a message out loud", "bad handshake",
            ],
            "Animals": [
                "penguin", "giraffe", "octopus", "sloth", "hamster",
                "goldfish", "panda", "kangaroo", "flamingo", "turtle",
                "dolphin", "owl", "butterfly", "crocodile", "zebra",
                "elephant", "monkey", "cat", "dog", "bee",
                "snake", "frog", "seal", "peacock", "hedgehog",
            ],
            "Movies/TV": [
                "superhero landing", "plot twist", "space adventure", "pirate ship", "detective mystery",
                "wizard school", "robot sidekick", "time travel", "alien invasion", "game show host",
                "cooking competition", "dance finale", "car chase", "romantic comedy", "animated musical",
                "news anchor", "sports commentator", "secret agent", "supervillain laugh", "dramatic courtroom",
                "monster under the bed", "cliffhanger ending", "laugh track", "mystery box", "training montage",
            ],
            "Professions": [
                "firefighter", "teacher", "nurse", "chef", "pilot",
                "astronaut", "mail carrier", "photographer", "mechanic", "scientist",
                "artist", "dentist", "lifeguard", "barber", "architect",
                "software developer", "gardener", "police officer", "bus driver", "farmer",
                "veterinarian", "news reporter", "carpenter", "zookeeper", "coach",
            ],
            "Everyday Objects": [
                "umbrella", "shopping cart", "toothbrush", "coffee mug", "remote control",
                "sunglasses", "backpack", "alarm clock", "rubber duck", "teddy bear",
                "flashlight", "water bottle", "key ring", "sticky note", "blanket",
                "pillow", "lunch box", "soccer ball", "paintbrush", "hairbrush",
                "tape dispenser", "doorbell", "vacuum cleaner", "headphones", "wallet",
            ],
            "Actions": [
                "brushing your teeth", "washing dishes", "doing the moonwalk", "jumping rope", "blowing bubbles",
                "building a sandcastle", "sneaking quietly", "tiptoeing", "opening a stuck jar", "baking cookies",
                "catching a bus", "reading a map", "tying shoelaces", "taking a selfie", "rowing a boat",
                "climbing a ladder", "playing the violin", "dribbling a basketball", "walking a dog", "painting a wall",
                "balancing on one foot", "pretending to be a robot", "inflating a balloon", "stirring soup", "shivering from cold",
            ],
        }

    def _make_word_bank_de(self):
        return {
            "Classic": [
                "luftgitarre", "bananenschale", "lagerfeuer", "schneeballschlacht", "geburtstagsparty",
                "gehirnfrost", "aufzug", "jonglieren", "pirat", "geist",
                "zombiegang", "hula-hoop", "eislaufen", "spaghetti schlürfen", "auf stelzen laufen",
                "clown", "cowboy", "dinosaurier", "feuerwerk", "kitzelmonster",
                "kissenschlacht", "papierflugzeug", "drachen steigen lassen", "geschenk auspacken", "high five",
            ],
            "Cringe": [
                "antwort-an-alle-katastrophe", "mikro nicht stumm", "kamera an im pyjama", "autokorrektur-fail", "peinlicher high five",
                "influencer-entschuldigung", "video puffert", "tippen und dann verschwinden", "versehentlicher taschenanruf", "falscher gruppenchat",
                "dir auch sagen", "doppelt schreiben", "jemandes namen vergessen", "schlechter wortwitz", "papa-tanz",
                "über den eigenen witz lachen", "kaffee verschütten", "stimmenbruch", "bei falscher person winken", "tür zu lange aufhalten",
                "über nichts stolpern", "zoom-filter-fehler", "posten und löschen", "nachricht laut vorlesen", "schlechter händedruck",
            ],
            "Animals": [
                "pinguin", "giraffe", "oktopus", "faultier", "hamster",
                "goldfisch", "panda", "känguru", "flamingo", "schildkröte",
                "delfin", "eule", "schmetterling", "krokodil", "zebra",
                "elefant", "affe", "katze", "hund", "biene",
                "schlange", "frosch", "robbe", "pfau", "igel",
            ],
            "Movies/TV": [
                "superhelden-landung", "plot twist", "weltraumabenteuer", "piratenschiff", "detektivfall",
                "zauberschule", "roboter-sidekick", "zeitreise", "alieninvasion", "gameshow-moderator",
                "kochshow-wettbewerb", "tanzfinale", "autoverfolgungsjagd", "romantische komödie", "animiertes musical",
                "nachrichtensprecher", "sportkommentator", "geheimagent", "superschurkenlachen", "dramatischer gerichtssaal",
                "monster unterm bett", "cliffhanger-ende", "lachspur", "mystery-box", "trainingsmontage",
            ],
            "Professions": [
                "feuerwehrmann", "lehrer", "pfleger", "koch", "pilot",
                "astronaut", "postbote", "fotograf", "mechaniker", "wissenschaftler",
                "künstler", "zahnarzt", "bademeister", "friseur", "architekt",
                "softwareentwickler", "gärtner", "polizist", "busfahrer", "bauer",
                "tierarzt", "reporter", "tischler", "zoo-wärter", "trainer",
            ],
            "Everyday Objects": [
                "regenschirm", "einkaufswagen", "zahnbürste", "kaffeebecher", "fernbedienung",
                "sonnenbrille", "rucksack", "wecker", "gummiente", "teddybär",
                "taschenlampe", "wasserflasche", "schlüsselbund", "haftnotiz", "decke",
                "kissen", "brotbox", "fußball", "pinsel", "haarbürste",
                "klebebandabroller", "türklingel", "staubsauger", "kopfhörer", "geldbeutel",
            ],
            "Actions": [
                "zähne putzen", "geschirr spülen", "den moonwalk machen", "seilspringen", "seifenblasen pusten",
                "sandburg bauen", "leise schleichen", "auf zehenspitzen gehen", "ein festsitzendes glas öffnen", "kekse backen",
                "einen bus erwischen", "eine karte lesen", "schnürsenkel binden", "ein selfie machen", "ein boot rudern",
                "eine leiter hochklettern", "geige spielen", "basketball dribbeln", "einen hund ausführen", "eine wand streichen",
                "auf einem bein balancieren", "so tun, als wärst du ein roboter", "einen ballon aufblasen", "suppe umrühren", "vor kälte zittern",
            ],
        }

    # ---------- UI helpers ----------
    def clear(self):
        if self.root is not None:
            set_visible(self.root, False)

        self.root = Entity(parent=camera.ui)

        # Background layer (NOT scaled)
        self.bg_root = Entity(parent=self.root)

        # UI layer (scaled on mobile)
        self.ui_root = Entity(parent=self.root)
        try:
            s = getattr(self.layout, 'ui_scale', 1.0)
            safe_setattr(self.ui_root, 'scale', (s, s))
        except Exception:
            pass

    def quad(self, x, y, w, h, c, z=0.0, parent=None):
        if parent is None:
            parent = self.ui_root if self.ui_root is not None else self.root

        e = Entity(parent=parent)
        safe_setattr(e, 'model', 'quad')
        safe_setattr(e, 'x', x)
        safe_setattr(e, 'y', y)
        safe_setattr(e, 'scale', (w, h))
        safe_setattr(e, 'color', c)
        safe_setattr(e, 'z', z)
        return e

    def txt(self, t, x=0, y=0, s=1.0, c=WHITE, parent=None):
        if parent is None:
            parent = self.ui_root if self.ui_root is not None else self.root

        tf = self._tf()
        t0 = Text(parent=parent, text=self._tr(t))
        safe_setattr(t0, 'x', x)
        safe_setattr(t0, 'y', y)
        safe_setattr(t0, 'scale', s * tf)
        safe_setattr(t0, 'origin', (0, 0))
        safe_setattr(t0, 'color', c)
        return t0

    def btn(self, label, x, y, on_click, w=0.60, h=0.10, bg=None, fg=None, text_scale=1.0, parent=None):
        if parent is None:
            parent = self.ui_root if self.ui_root is not None else self.root

        b = Button(parent=parent, text=self._tr(label))
        safe_setattr(b, 'model', 'quad')
        safe_setattr(b, 'x', x)
        safe_setattr(b, 'y', y)
        safe_setattr(b, 'scale', (w, h))
        style_button(b, bg if bg is not None else self.C_BTN_DARK, fg if fg is not None else WHITE)
        b.on_click = on_click

        try:
            if hasattr(b, 'text_entity') and b.text_entity is not None:
                b.text_entity.scale = b.text_entity.scale * text_scale
        except Exception:
            pass

        return b

    def stripes(self):
        l = self.layout
        w = max(1.35, (l.half_w * 2) + 0.40)
        h = 0.95

        self.quad(0, 0, w, h, self.C_BG, z=0.02, parent=self.bg_root)

        stripe_w = w / 6
        start_x = -w / 2 + stripe_w / 2
        cols = [self.C_STRIPE1, self.C_STRIPE2, self.C_STRIPE3, self.C_STRIPE2, self.C_STRIPE1, self.C_STRIPE3]
        for i in range(6):
            x = start_x + i * stripe_w
            self.quad(x, 0, stripe_w * 0.98, h, cols[i], z=0.021, parent=self.bg_root)

    # ---------- Timers ----------
    def stop_all_timers(self):
        self.scheduler.clear_interval(self._round_interval)
        self.scheduler.clear_interval(self._countdown_interval)
        self.scheduler.clear_timeout(self._flash_timeout)
        self._round_interval = None
        self._countdown_interval = None
        self._flash_timeout = None

    def start_countdown(self, n=3):
        self.scheduler.clear_interval(self._countdown_interval)
        self._countdown_interval = None

        self.phase = self.PHASE_COUNTDOWN
        self.countdown_value = n

        set_visible(self.countdown_text, True)
        self.countdown_text.text = str(self.countdown_value)

        self._countdown_interval = self.scheduler.set_interval(self._countdown_tick, 1.0)
        if self._countdown_interval is None:
            set_visible(self.countdown_text, False)
            self.begin_round()

    def _countdown_tick(self):
        if self.state != self.STATE_GAMEPLAY or self.phase != self.PHASE_COUNTDOWN or self.paused:
            return

        self.countdown_value -= 1
        if self.countdown_value <= 0:
            self.scheduler.clear_interval(self._countdown_interval)
            self._countdown_interval = None
            set_visible(self.countdown_text, False)
            self.begin_round()
            return

        self.countdown_text.text = str(self.countdown_value)

    def start_round_timer(self):
        self.scheduler.clear_interval(self._round_interval)
        self._round_interval = None

        self._round_interval = self.scheduler.set_interval(self._timer_tick, 1.0)
        if self._round_interval is None:
            self.message_text.text = self._tr("Timer backend failed — use End Round.")
            safe_setattr(self.message_text, 'color', self.C_WARN)

    def _timer_tick(self):
        if self.state != self.STATE_GAMEPLAY or self.phase != self.PHASE_PLAYING or self.paused:
            return

        self.time_left -= 1
        if self.time_left < 0:
            self.time_left = 0

        if self.timer_text is not None:
            self.timer_text.text = f"{self.time_left}s"
        self.update_timer_bar()

        if self.time_left <= 0:
            self.scheduler.clear_interval(self._round_interval)
            self._round_interval = None
            self.end_round()

    def flash(self, msg, c):
        if self.message_text is None:
            return
        self.message_text.text = self._tr(msg)
        safe_setattr(self.message_text, 'color', c)

        self.scheduler.clear_timeout(self._flash_timeout)
        self._flash_timeout = self.scheduler.set_timeout(self._flash_revert, 1.0)

    def _flash_revert(self):
        if self.message_text is not None:
            safe_setattr(self.message_text, 'color', SMOKE)

    # ---------- State machine ----------
    def go(self, state):
        if self.state == self.STATE_GAMEPLAY and state != self.STATE_GAMEPLAY:
            self.stop_all_timers()

        self.state = state
        self.layout = Layout()
        self.clear()

        if state == self.STATE_MENU:
            self.build_menu()
        elif state == self.STATE_SETUP:
            self.build_setup()
        elif state == self.STATE_SETTINGS:
            self.build_settings()
        elif state == self.STATE_HOWTO:
            self.build_howto()
        elif state == self.STATE_GAMEPLAY:
            self.build_gameplay()
        elif state == self.STATE_SUMMARY:
            self.build_summary()
        elif state == self.STATE_FINAL:
            self.build_final()

    # ---------- Screens ----------
    def build_menu(self):
        l = self.layout
        self.stripes()

        panel_w = min(1.12, l.w + 0.10)
        self.quad(0, 0, panel_w, 0.78, self.C_PANEL, z=0.03)
        self.txt("CHARADES", y=0.30, s=2.5, c=self.C_PRIMARY)
        self.txt("Pantomime / Charades (2D)", y=0.22, s=1.2)

        bw = min(0.75, panel_w * 0.90)
        self.btn("Play", 0, 0.08, lambda: self.go(self.STATE_SETUP), w=bw, h=0.12, bg=self.C_PRIMARY, fg=BLACK)
        self.btn("Settings", 0, -0.05, lambda: self.go(self.STATE_SETTINGS), w=bw, h=0.11, bg=self.C_BTN_DARK, fg=WHITE)
        self.btn("How To Play", 0, -0.18, lambda: self.go(self.STATE_HOWTO), w=bw, h=0.11, bg=self.C_BTN_DARK, fg=WHITE)
        self.btn("Quit", 0, -0.31, self.show_quit, w=bw, h=0.11, bg=self.C_BAD, fg=BLACK)

        if not (HAS_BRYTHON_TIMER and l.is_portrait):
            self.txt(f"Timer backend: {self.scheduler.backend}", y=-0.44, s=0.7, c=SMOKE)

    def show_quit(self):
        self.clear()
        self.stripes()
        self.quad(0, 0, 1.05, 0.55, self.C_PANEL, z=0.03)
        self.txt("Quit", y=0.18, s=2.0, c=self.C_BAD)
        self.txt(".Browser: close the tab to quit\n.Desktop: close the window to quit", y=0.00, s=1.1)
        self.btn("Back", 0, -0.18, lambda: self.go(self.STATE_MENU), bg=self.C_PRIMARY, fg=BLACK)

    def build_settings(self):
        self.stripes()
        self.quad(0, 0, 1.18, 0.70, self.C_PANEL, z=0.03)
        self.txt("Settings", y=0.30, s=2.0, c=self.C_PRIMARY)

        def toggle_lang():
            self.language = 'de' if self.language != 'de' else 'en'
            try:
                self.selector.bank = self._active_word_bank()
            except Exception:
                pass
            self.go(self.STATE_SETTINGS)

        # ✅ moved ABOVE pass penalty
        self.btn("English / Deutsch", 0, 0.20, toggle_lang, w=0.90, h=0.11,
                 bg=self.C_BTN_DARK, fg=WHITE)

        pass_label = "Pass penalty: OFF (0)" if self.pass_penalty == 0 else "Pass penalty: ON (-1)"
        auto_label = "Auto-next word: ON" if self.auto_next_word else "Auto-next word: OFF"

        def toggle_pass():
            self.pass_penalty = -1 if self.pass_penalty == 0 else 0
            self.go(self.STATE_SETTINGS)

        def toggle_auto():
            self.auto_next_word = not self.auto_next_word
            self.go(self.STATE_SETTINGS)

        self.btn(pass_label, 0, 0.06, toggle_pass, w=0.90, h=0.11,
                 bg=self.C_WARN if self.pass_penalty else self.C_BTN_DARK,
                 fg=BLACK if self.pass_penalty else WHITE)

        self.btn(auto_label, 0, -0.08, toggle_auto, w=0.90, h=0.11,
                 bg=self.C_PRIMARY if self.auto_next_word else self.C_BTN_DARK,
                 fg=BLACK if self.auto_next_word else WHITE)

        self.btn("Back", 0, -0.28, lambda: self.go(self.STATE_MENU), bg=self.C_BTN_DARK, fg=WHITE)

    def build_howto(self):
        self.stripes()
        self.quad(0, 0, 1.22, 0.82, self.C_PANEL, z=0.03)
        self.txt("How To Play", y=0.34, s=2.0, c=self.C_PRIMARY)

        how = (
            ".One player acts the word silently •\n"
            ".Teammates guess •\n"
            ".Tap Reveal Word → 3…2…1 → timer starts •\n"
            ".Correct = +1 point •\n"
            ".Pass = 0 or -1 (Settings) •\n"
            ".End Round ends early •\n"
            ".Teams rotate turns. Highest score wins •"
        )
        self.txt(how, y=0.05, s=1.0, c=SMOKE)
        self.btn("Back", 0, -0.34, lambda: self.go(self.STATE_MENU), bg=self.C_PRIMARY, fg=BLACK)

    # --------- Setup ----------
    def build_setup(self):
        l = self.layout
        self.stripes()
        self.quad(0, 0, 1.26, 0.90, self.C_PANEL, z=0.03)

        if HAS_BRYTHON_TIMER and l.is_narrow:
            self.build_setup_mobile()
        else:
            self.build_setup_desktop()

    def build_setup_desktop(self):
        self.txt("Setup", y=0.41, s=2.2, c=self.C_PRIMARY)

        t_val = self.txt(str(self.num_teams), x=0.30, y=0.24, s=1.4)
        d_val = self.txt(str(self.round_duration) + "s", x=0.30, y=0.14, s=1.4)
        r_val = self.txt(str(self.rounds_per_team), x=0.30, y=0.04, s=1.4)

        self.txt("Teams (1–4)", x=-0.30, y=0.24, s=1.1)
        self.txt("Round time", x=-0.30, y=0.14, s=1.1)
        self.txt("Rounds / team", x=-0.30, y=0.04, s=1.1)

        def set_teams(d):
            self.num_teams = max(1, min(4, self.num_teams + d))
            t_val.text = str(self.num_teams)

        def set_time(d):
            opts = [30, 60, 90]
            try:
                i = opts.index(self.round_duration)
            except Exception:
                i = 1
            i = max(0, min(len(opts) - 1, i + d))
            self.round_duration = opts[i]
            d_val.text = str(self.round_duration) + "s"

        def set_rounds(d):
            self.rounds_per_team = max(1, min(10, self.rounds_per_team + d))
            r_val.text = str(self.rounds_per_team)

        self.btn("-", 0.12, 0.24, lambda: set_teams(-1), w=0.10, h=0.08, bg=self.C_BTN_DARK, fg=WHITE)
        self.btn("+", 0.48, 0.24, lambda: set_teams(+1), w=0.10, h=0.08, bg=self.C_BTN_DARK, fg=WHITE)

        self.btn("-", 0.12, 0.14, lambda: set_time(-1), w=0.10, h=0.08, bg=self.C_BTN_DARK, fg=WHITE)
        self.btn("+", 0.48, 0.14, lambda: set_time(+1), w=0.10, h=0.08, bg=self.C_BTN_DARK, fg=WHITE)

        self.btn("-", 0.12, 0.04, lambda: set_rounds(-1), w=0.10, h=0.08, bg=self.C_BTN_DARK, fg=WHITE)
        self.btn("+", 0.48, 0.04, lambda: set_rounds(+1), w=0.10, h=0.08, bg=self.C_BTN_DARK, fg=WHITE)

        self.txt("Categories (multi-select)", y=-0.08, s=1.15, c=SMOKE)

        cat_colors = {
            "Classic": hsv(60,  1.00, 0.95),
            "Cringe":  hsv(320, 0.75, 0.95),
            "Animals": hsv(120, 0.80, 0.90),
            "Movies/TV": hsv(210, 0.80, 0.95),
            "Professions": hsv(30, 1.00, 0.95),
            "Everyday Objects": hsv(250, 0.30, 0.95),
            "Actions": hsv(180, 0.70, 0.95),
        }

        cats = list(self._active_word_bank().keys())
        start_y = -0.16
        dy = 0.07

        l = self.layout
        gap = 0.04
        btn_w = (l.w - gap) / 2.0
        btn_w = clamp(btn_w, 0.36, 0.46)
        x_left = l.left + btn_w / 2.0
        x_right = l.right - btn_w / 2.0

        def toggle_cat(name):
            # empty selection means ALL categories are active
            if not self.selected_categories:
                # first click turns on "filter mode" with only this category
                self.selected_categories = {name}
            else:
                # normal toggle mode
                if name in self.selected_categories:
                    self.selected_categories.remove(name)
                else:
                    self.selected_categories.add(name)
            self.go(self.STATE_SETUP)

        for i, name in enumerate(cats):
            x = x_left if (i % 2 == 0) else x_right
            y = start_y - (i // 2) * dy
            on = (not self.selected_categories) or (name in self.selected_categories)
            bg = cat_colors.get(name, self.C_PRIMARY) if on else self.C_BTN_DARK
            fg = BLACK if on else WHITE
            self.btn(name, x, y, on_click=lambda n=name: toggle_cat(n), w=btn_w, h=0.065, bg=bg, fg=fg)

        def start_game():
            active_bank = self._active_word_bank()
            self.selector.bank = active_bank if active_bank else self.word_bank

            if self.selected_categories:
                cats_to_use = [c for c in self.selected_categories if c in self.selector.bank]
                if not cats_to_use:
                    cats_to_use = list(self.selector.bank.keys())
            else:
                cats_to_use = list(self.selector.bank.keys())

            self.selector.set_categories(cats_to_use)
            self.scores = [0 for _ in range(self.num_teams)]
            self.turn_index = 0
            self.go(self.STATE_GAMEPLAY)

        self.btn("Start Game", 0, -0.46, start_game, w=0.84, h=0.11, bg=self.C_PRIMARY, fg=BLACK)
        self.btn("Back", -0.55, 0.45, lambda: self.go(self.STATE_MENU), w=0.16, h=0.07, bg=self.C_BTN_DARK, fg=WHITE)

    def build_setup_mobile(self):
        l = self.layout
        self.txt("Setup", y=l.top - 0.06, s=2.1, c=self.C_PRIMARY)

        self.btn("Back", l.left + 0.16, l.top - 0.02, lambda: self.go(self.STATE_MENU),
                 w=0.22, h=0.07, bg=self.C_BTN_DARK, fg=WHITE)

        btn_w = 0.18
        btn_h = 0.075
        x_minus = l.left + 0.20
        x_plus = l.right - 0.20
        x_val = 0.0

        self.txt("Teams (1–4)", y=0.27, s=1.0, c=SMOKE)
        t_val = self.txt(str(self.num_teams), x=x_val, y=0.21, s=1.5, c=WHITE)

        self.txt("Round time", y=0.14, s=1.0, c=SMOKE)
        d_val = self.txt(str(self.round_duration) + "s", x=x_val, y=0.08, s=1.5, c=WHITE)

        self.txt("Rounds / team", y=0.01, s=1.0, c=SMOKE)
        r_val = self.txt(str(self.rounds_per_team), x=x_val, y=-0.05, s=1.5, c=WHITE)

        def set_teams(d):
            self.num_teams = max(1, min(4, self.num_teams + d))
            t_val.text = str(self.num_teams)

        def set_time(d):
            opts = [30, 60, 90]
            try:
                i = opts.index(self.round_duration)
            except Exception:
                i = 1
            i = max(0, min(len(opts) - 1, i + d))
            self.round_duration = opts[i]
            d_val.text = str(self.round_duration) + "s"

        def set_rounds(d):
            self.rounds_per_team = max(1, min(10, self.rounds_per_team + d))
            r_val.text = str(self.rounds_per_team)

        self.btn("-", x_minus, 0.21, lambda: set_teams(-1), w=btn_w, h=btn_h, bg=self.C_BTN_DARK, fg=WHITE)
        self.btn("+", x_plus, 0.21, lambda: set_teams(+1), w=btn_w, h=btn_h, bg=self.C_BTN_DARK, fg=WHITE)

        self.btn("-", x_minus, 0.08, lambda: set_time(-1), w=btn_w, h=btn_h, bg=self.C_BTN_DARK, fg=WHITE)
        self.btn("+", x_plus, 0.08, lambda: set_time(+1), w=btn_w, h=btn_h, bg=self.C_BTN_DARK, fg=WHITE)

        self.btn("-", x_minus, -0.05, lambda: set_rounds(-1), w=btn_w, h=btn_h, bg=self.C_BTN_DARK, fg=WHITE)
        self.btn("+", x_plus, -0.05, lambda: set_rounds(+1), w=btn_w, h=btn_h, bg=self.C_BTN_DARK, fg=WHITE)

        self.txt("Categories", y=-0.13, s=1.05, c=SMOKE)

        cat_colors = {
            "Classic": hsv(60,  1.00, 0.95),
            "Cringe":  hsv(320, 0.75, 0.95),
            "Animals": hsv(120, 0.80, 0.90),
            "Movies/TV": hsv(210, 0.80, 0.95),
            "Professions": hsv(30, 1.00, 0.95),
            "Everyday Objects": hsv(250, 0.30, 0.95),
            "Actions": hsv(180, 0.70, 0.95),
        }

        disp = {
            "Movies/TV": "Movies",
            "Everyday Objects": "Objects",
            "Professions": "Jobs",
        }

        cats = list(self._active_word_bank().keys())

        cols = 4
        gap = 0.02

        # EXTRA SAFE MARGIN (prevents iPhone left/right crop)
        outer_pad = 0.08
        grid_left = l.left + outer_pad
        grid_right = l.right - outer_pad
        grid_w = grid_right - grid_left

        b_w = (grid_w - gap * (cols - 1)) / cols
        b_w = clamp(b_w, 0.15, 0.21)
        b_h = 0.065
        start_y = -0.18
        dy = 0.08

        x0 = grid_left + b_w / 2
        x_cols = [x0 + i * (b_w + gap) for i in range(cols)]

        def toggle_cat(name):
            # empty selection means ALL categories are active
            if not self.selected_categories:
                self.selected_categories = {name}
            else:
                if name in self.selected_categories:
                    self.selected_categories.remove(name)
                else:
                    self.selected_categories.add(name)
            self.go(self.STATE_SETUP)

        for i, name in enumerate(cats):
            col = i % cols
            row = i // cols
            x = x_cols[col]
            y = start_y - row * dy

            on = (not self.selected_categories) or (name in self.selected_categories)
            bg = cat_colors.get(name, self.C_PRIMARY) if on else self.C_BTN_DARK
            fg = BLACK if on else WHITE
            label = disp.get(name, name)

            self.btn(label, x, y, on_click=lambda n=name: toggle_cat(n),
                     w=b_w, h=b_h, bg=bg, fg=fg, text_scale=0.85)

        def start_game():
            active_bank = self._active_word_bank()
            self.selector.bank = active_bank if active_bank else self.word_bank

            if self.selected_categories:
                cats_to_use = [c for c in self.selected_categories if c in self.selector.bank]
                if not cats_to_use:
                    cats_to_use = list(self.selector.bank.keys())
            else:
                cats_to_use = list(self.selector.bank.keys())

            self.selector.set_categories(cats_to_use)
            self.scores = [0 for _ in range(self.num_teams)]
            self.turn_index = 0
            self.go(self.STATE_GAMEPLAY)

        start_h = 0.085
        start_w = clamp(l.w - 0.16, 0.64, 0.82)  # narrower so it never hits cropped edges
        start_y_btn = l.bottom + start_h / 2

        self.btn("Start Game", 0, start_y_btn, start_game,
                 w=start_w, h=start_h, bg=self.C_PRIMARY, fg=BLACK, text_scale=0.95)

    # ---------- Gameplay ----------
    def build_gameplay(self):
        self.stop_all_timers()
        l = self.layout

        self.stripes()
        self.quad(0, 0, 1.30, 0.92, self.C_PANEL, z=0.03)

        self.phase = self.PHASE_REVEAL
        self.paused = False
        self.phase_before_pause = None
        self.round_points = 0
        self.time_left = self.round_duration
        self.current_word = ''
        self.waiting_for_next = False

        team_i = self.turn_index % self.num_teams
        round_no = (self.turn_index // self.num_teams) + 1
        team_c = self.team_colors[team_i % len(self.team_colors)]

        header_scores = HAS_BRYTHON_TIMER

        header_h = 0.14 if header_scores else 0.10
        header_y = l.top - header_h / 2
        self.quad(0, header_y, 1.22, header_h, team_c, z=0.04)

        if header_scores:
            self.txt(f"Team {team_i+1} • Round {round_no}/{self.rounds_per_team}", y=header_y + 0.03, s=1.10, c=BLACK)
            self.header_score_text = self.txt("", y=header_y - 0.03, s=0.95, c=BLACK)
        else:
            self.header_score_text = None
            self.txt(f"Team {team_i+1}  •  Round {round_no}/{self.rounds_per_team}", y=header_y, s=1.25, c=BLACK)

        pause_x = (l.left + 0.08) if HAS_BRYTHON_TIMER else (l.right - 0.10)
        pause_y = header_y
        self.btn_pause = self.btn("Pause", pause_x, pause_y, self.toggle_pause, w=0.18, h=0.07, bg=self.C_BTN_DARK, fg=WHITE)

        timer_y = header_y - 0.18 if header_scores else 0.34
        self.timer_text = self.txt(f"{self.time_left}s", y=timer_y, s=2.0, c=WHITE)

        # Word panel
        wp_w = 1.18 if not HAS_BRYTHON_TIMER else min(1.18, l.w * 1.25)
        self.quad(0, 0.08, wp_w, 0.30, self.C_PANEL2, z=0.04)

        self.word_text = self.txt("(Word hidden)", y=0.10, s=2.0, c=WHITE)

        if HAS_BRYTHON_TIMER:
            msg = ".Only the actor should see\n.Tap Reveal Word"
            msg_scale = 0.95
        else:
            msg = ".Tap Reveal Word when only the actor can see"
            msg_scale = 1.0
        self.message_text = self.txt(msg, y=-0.06, s=msg_scale, c=SMOKE)

        # ✅ TIMER BAR (thinner + moved up on mobile so it doesn't overlap text)
        bar_w = 0.6 if not HAS_BRYTHON_TIMER else min(0.6, l.w - 0.12)

        if HAS_BRYTHON_TIMER:
            # thinner bar in browser/mobile
            bar_h = 0.025
            # move bar up (just under the header), away from the word text/panel
            bar_y = (header_y - header_h / 2) - 0.03
        else:
            bar_h = 0.03
            bar_y = timer_y - 0.06

        self.timer_bar_bg = self.quad(0, bar_y, bar_w, bar_h, hsv(0, 0, 0.25), z=0.04)
        self.timer_bar_fill = self.quad(0, bar_y, bar_w, bar_h, team_c, z=0.041)

        self.countdown_text = self.txt("", y=0.20, s=4.5, c=hsv(60, 0.60, 1.00))
        set_visible(self.countdown_text, False)

        reveal_y = -0.20 if HAS_BRYTHON_TIMER else -0.22
        self.btn_word_action = self.btn("Reveal Word", 0, reveal_y, self.on_word_action,
                                        w=(l.w * 0.94 if HAS_BRYTHON_TIMER else 0.84),
                                        h=0.12, bg=self.C_PRIMARY, fg=BLACK)

        if HAS_BRYTHON_TIMER:
            # keep buttons WELL inside safe area (fix iPhone crop)
            inner_pad = 0.10
            left_edge = l.left + inner_pad
            right_edge = l.right - inner_pad

            gap = 0.03
            act_h = 0.105
            btn_y = l.bottom + act_h / 2

            row_w = right_edge - left_edge
            btn_w = (row_w - 2 * gap) / 3.0

            x_left = left_edge + btn_w / 2
            x_mid = (left_edge + right_edge) / 2.0
            x_right = right_edge - btn_w / 2

            self.btn_correct = self.btn("Correct (+1)", x_left, btn_y, self.on_correct,
                                        w=btn_w, h=act_h, bg=self.C_GOOD, fg=BLACK, text_scale=0.90)
            self.btn_pass = self.btn(f"Pass ({self.pass_penalty})", x_mid, btn_y, self.on_pass,
                                     w=btn_w, h=act_h, bg=self.C_WARN, fg=BLACK, text_scale=0.90)
            self.btn_end = self.btn("End Round", x_right, btn_y, self.end_round,
                                    w=btn_w, h=act_h, bg=self.C_BAD, fg=BLACK, text_scale=0.90)
        else:
            self.btn_correct = self.btn("Correct (+1)", -0.34, -0.38, self.on_correct, w=0.34, h=0.12, bg=self.C_GOOD, fg=BLACK)
            self.btn_pass = self.btn(f"Pass ({self.pass_penalty})", 0.00, -0.38, self.on_pass, w=0.34, h=0.12, bg=self.C_WARN, fg=BLACK)
            self.btn_end = self.btn("End Round", 0.34, -0.38, self.end_round, w=0.34, h=0.12, bg=self.C_BAD, fg=BLACK)

        set_visible(self.btn_correct, False)
        set_visible(self.btn_pass, False)
        set_visible(self.btn_end, False)

        self.score_texts = []
        self.score_rows = []
        self.score_panel = None
        self.score_title = None

        if not header_scores:
            sx = l.right - 0.22
            self.score_panel = self.quad(sx, 0.00, 0.38, 0.55, self.C_PANEL2, z=0.04)
            self.score_title = self.txt("SCORES", x=sx, y=0.22, s=1.1, c=SMOKE)

            for i in range(self.num_teams):
                yy = 0.13 - i * 0.09
                row = self.quad(sx, yy, 0.33, 0.07, hsv(230, 0.15, 0.30), z=0.041)
                tx = self.txt("", x=sx, y=yy, s=0.95, c=self.team_colors[i % len(self.team_colors)])
                self.score_rows.append(row)
                self.score_texts.append(tx)

        self.refresh_scores()
        self.update_timer_bar()

        self.build_pause_overlay()
        self.show_pause(False)

    def update_timer_bar(self):
        if self.timer_bar_bg is None or self.timer_bar_fill is None:
            return

        total = self.round_duration if self.round_duration > 0 else 1
        ratio = self.time_left / total
        ratio = clamp(ratio, 0.0, 1.0)

        base_w = 0.6
        bar_h = 0.03
        bar_x = 0.0

        try:
            s = self.timer_bar_bg.scale
            if isinstance(s, (tuple, list)) and len(s) >= 2:
                base_w = float(s[0])
                bar_h = float(s[1])
            elif hasattr(s, 'x') and hasattr(s, 'y'):
                base_w = float(s.x)
                bar_h = float(s.y)

            if hasattr(self.timer_bar_bg, 'x'):
                bar_x = float(self.timer_bar_bg.x)
        except Exception:
            pass

        w = base_w * ratio
        left_edge = bar_x - base_w / 2.0

        safe_setattr(self.timer_bar_fill, 'scale', (w, bar_h))
        safe_setattr(self.timer_bar_fill, 'x', left_edge + w / 2.0)

    def refresh_scores(self):
        current = self.turn_index % self.num_teams

        if self.header_score_text is not None:
            parts = []
            for i in range(self.num_teams):
                if i == current:
                    parts.append(f"[T{i+1}:{self.scores[i]}]")
                else:
                    parts.append(f"T{i+1}:{self.scores[i]}")
            self.header_score_text.text = "   ".join(parts)
            return

        for i in range(self.num_teams):
            marker = "▶ " if i == current else "  "
            self.score_texts[i].text = f"{marker}Team {i+1}: {self.scores[i]}"
            bg = hsv(230, 0.18, 0.36) if i == current else hsv(230, 0.15, 0.30)
            safe_setattr(self.score_rows[i], 'color', bg)

    def build_pause_overlay(self):
        self.pause_overlay = self.quad(0, 0, 1.35, 0.95, hsv(0, 0, 0, 0.66), z=0.20)
        self.pause_panel = self.quad(0, 0.02, 0.95, 0.52, self.C_PANEL2, z=0.21)
        self.pause_label = self.txt("Paused", y=0.14, s=2.0, c=self.C_PRIMARY)
        self.pause_btn_resume = self.btn("Resume", 0, 0.00, self.toggle_pause, w=0.60, h=0.10, bg=self.C_PRIMARY, fg=BLACK)
        self.pause_btn_menu = self.btn("Back to Menu", 0, -0.14, lambda: self.go(self.STATE_MENU), w=0.60, h=0.10, bg=self.C_BTN_DARK, fg=WHITE)

    def show_pause(self, show):
        for e in [self.pause_overlay, self.pause_panel, self.pause_label, self.pause_btn_resume, self.pause_btn_menu]:
            set_visible(e, show)

        if show:
            set_visible(self.btn_correct, False)
            set_visible(self.btn_pass, False)
            set_visible(self.btn_end, False)
            set_visible(self.btn_word_action, False)
        else:
            if self.phase == self.PHASE_PLAYING:
                set_visible(self.btn_correct, True)
                set_visible(self.btn_pass, True)
                set_visible(self.btn_end, True)
                if self.waiting_for_next:
                    set_visible(self.btn_word_action, True)

    # ---------- Gameplay actions ----------
    def on_word_action(self):
        if self.state != self.STATE_GAMEPLAY or self.paused:
            return

        if self.phase == self.PHASE_REVEAL:
            self.current_word = self.selector.next_word()
            self.word_text.text = self.current_word
            self.message_text.text = " "  # "3... 2... 1... Go!"
            set_visible(self.btn_word_action, False)
            self.start_countdown(3)
            return

        if self.phase == self.PHASE_PLAYING and self.waiting_for_next:
            self.word_text.text = self.current_word
            self.waiting_for_next = False
            set_visible(self.btn_word_action, False)

    def begin_round(self):
        self.phase = self.PHASE_PLAYING
        self.round_points = 0
        self.time_left = self.round_duration
        self.timer_text.text = f"{self.time_left}s"
        self.update_timer_bar()

        set_visible(self.btn_correct, True)
        set_visible(self.btn_pass, True)
        set_visible(self.btn_end, True)

        self.start_round_timer()

    def on_correct(self):
        if self.state != self.STATE_GAMEPLAY or self.phase != self.PHASE_PLAYING or self.paused:
            return

        team_i = self.turn_index % self.num_teams
        self.scores[team_i] += 1
        self.round_points += 1
        self.refresh_scores()
        self.flash("Correct! +1", self.C_GOOD)

        if self.auto_next_word:
            self.current_word = self.selector.next_word()
            self.word_text.text = self.current_word
            self.waiting_for_next = False
            set_visible(self.btn_word_action, False)
        else:
            self.current_word = self.selector.next_word()
            self.word_text.text = self._tr("(Tap Next Word)")
            self.waiting_for_next = True
            self.btn_word_action.text = self._tr("Next Word")
            style_button(self.btn_word_action, self.C_PRIMARY, BLACK)
            set_visible(self.btn_word_action, True)

    def on_pass(self):
        if self.state != self.STATE_GAMEPLAY or self.phase != self.PHASE_PLAYING or self.paused:
            return

        team_i = self.turn_index % self.num_teams
        self.scores[team_i] += self.pass_penalty
        if self.scores[team_i] < 0:
            self.scores[team_i] = 0
        self.round_points += self.pass_penalty
        self.refresh_scores()

        self.flash("Pass" if self.pass_penalty == 0 else "Pass (-1)", self.C_WARN if self.pass_penalty == 0 else self.C_BAD)

        self.current_word = self.selector.next_word()
        self.word_text.text = self.current_word
        self.waiting_for_next = False
        set_visible(self.btn_word_action, False)

    def toggle_pause(self):
        if self.state != self.STATE_GAMEPLAY:
            return

        if not self.paused:
            self.paused = True
            self.phase_before_pause = self.phase
            self.phase = self.PHASE_PAUSED

            self.scheduler.clear_interval(self._round_interval)
            self.scheduler.clear_interval(self._countdown_interval)
            self._round_interval = None
            self._countdown_interval = None

            self.show_pause(True)
            return

        self.paused = False
        self.show_pause(False)

        prev = self.phase_before_pause
        self.phase_before_pause = None

        if prev == self.PHASE_COUNTDOWN:
            self.phase = self.PHASE_COUNTDOWN
            self._countdown_interval = self.scheduler.set_interval(self._countdown_tick, 1.0)
        elif prev == self.PHASE_PLAYING:
            self.phase = self.PHASE_PLAYING
            set_visible(self.btn_correct, True)
            set_visible(self.btn_pass, True)
            set_visible(self.btn_end, True)
            if self.waiting_for_next:
                set_visible(self.btn_word_action, True)
            self._round_interval = self.scheduler.set_interval(self._timer_tick, 1.0)
        else:
            self.phase = prev if prev is not None else self.PHASE_REVEAL

    def end_round(self):
        if self.state != self.STATE_GAMEPLAY:
            return
        self.stop_all_timers()
        self.go(self.STATE_SUMMARY)

    def build_summary(self):
        self.stripes()
        self.quad(0, 0, 1.15, 0.75, self.C_PANEL, z=0.03)

        team_i = self.turn_index % self.num_teams
        team_c = self.team_colors[team_i % len(self.team_colors)]

        self.txt("Round Summary", y=0.30, s=2.0, c=team_c)
        self.txt(f"Team {team_i+1} gained: {self.round_points}", y=0.16, s=1.4, c=SMOKE)

        lines = []
        for i, s0 in enumerate(self.scores):
            lines.append(f"Team {i+1}: {s0}")
        self.txt("\n".join(lines), y=-0.04, s=1.2, c=SMOKE)

        def next_turn():
            self.turn_index += 1
            if self.turn_index >= (self.num_teams * self.rounds_per_team):
                self.go(self.STATE_FINAL)
            else:
                self.go(self.STATE_GAMEPLAY)

        self.btn("Next Turn", 0, -0.30, next_turn, w=0.75, h=0.11, bg=self.C_PRIMARY, fg=BLACK)
        self.btn("Menu", 0, -0.42, lambda: self.go(self.STATE_MENU), w=0.75, h=0.10, bg=self.C_BTN_DARK, fg=WHITE)

    def build_final(self):
        self.stripes()
        self.quad(0, 0, 1.15, 0.78, self.C_PANEL, z=0.03)

        self.txt("Final Results", y=0.32, s=2.2, c=self.C_PRIMARY)

        best = 0
        if self.scores:
            best = self.scores[0]
            for s0 in self.scores:
                if s0 > best:
                    best = s0

        winners = [i + 1 for i, s0 in enumerate(self.scores) if s0 == best]

        if len(winners) == 1:
            wc = self.team_colors[(winners[0] - 1) % len(self.team_colors)]
            self.txt(f"Winner: Team {winners[0]} ({best})", y=0.18, s=1.5, c=wc)
        else:
            self.txt(f"Tie: Teams {', '.join([str(w) for w in winners])} ({best})", y=0.18, s=1.2, c=hsv(60, 0.60, 1.00))

        lines = [f"Team {i+1}: {s0}" for i, s0 in enumerate(self.scores)]
        self.txt("\n".join(lines), y=-0.02, s=1.2, c=SMOKE)

        def restart():
            self.scores = [0 for _ in range(self.num_teams)]
            self.turn_index = 0
            self.go(self.STATE_GAMEPLAY)

        self.btn("Restart", 0, -0.30, restart, w=0.75, h=0.11, bg=self.C_PRIMARY, fg=BLACK)
        self.btn("Back to Menu", 0, -0.42, lambda: self.go(self.STATE_MENU), w=0.75, h=0.10, bg=self.C_BTN_DARK, fg=WHITE)


# -----------------------
# Boot
# -----------------------
def boot():
    try:
        CharadesApp()
    except Exception as e:
        root = Entity(parent=camera.ui)
        p = Entity(parent=root)
        safe_setattr(p, 'model', 'quad')
        safe_setattr(p, 'scale', (1.2, 0.6))
        safe_setattr(p, 'color', hsv(340, 1, 1))
        Text(parent=root, text=f"Startup error:\n{e}")


try:
    app = Ursina()
except Exception:
    app = None

boot()

try:
    if app is not None and hasattr(app, 'run'):
        app.run()
except Exception:
    # Some Ursina CSS setups manage the loop externally
    pass
