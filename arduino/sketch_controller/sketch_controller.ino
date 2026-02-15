#include <Arduino.h>

/*
  --- SILICON OR SOUL: SMART CONSOLE FIRMWARE ---
  Hardware: Seeed Studio XIAO RP2040
  
  WIRING:
  - Ground: Common Ground for Buttons and LEDs
  - Silicon Button: D2 (Switch), D4 (LED +)
  - Soul Button:    D3 (Switch), D5 (LED +)
*/

// --- CONFIGURATION ---
// !!! CHANGE THIS FOR EACH BOARD !!!
// Options: "PLAYER_1", "PLAYER_2", "PLAYER_3"
const String PLAYER_ID = "PLAYER_1"; 

// --- PIN MAPPING (RP2040 Specific) ---
const int PIN_BTN_SILICON = D2; 
const int PIN_BTN_SOUL    = D3; 
const int PIN_LED_SILICON = D4; 
const int PIN_LED_SOUL    = D5; 

// --- GAME STATE ---
String currentVote = "NONE";
bool lockedIn = false;
bool choosingAnimation = false;
bool choosingSiliconOn = false;
unsigned long choosingLastToggleAt = 0;
const unsigned long CHOOSING_FLICKER_MS = 180;

void setup() {
  Serial.begin(9600);
  
  // Hardware Setup
  pinMode(PIN_BTN_SILICON, INPUT_PULLUP);
  pinMode(PIN_BTN_SOUL, INPUT_PULLUP);
  pinMode(PIN_LED_SILICON, OUTPUT);
  pinMode(PIN_LED_SOUL, OUTPUT);
  pinMode(LED_BUILTIN, OUTPUT); // Visual debug

  // USB Safety Wait (Max 3 seconds)
  // Ensures the connection is ready before we start talking
  unsigned long start = millis();
  while (!Serial && millis() - start < 3000) {
    delay(10);
  }
  
  // Boot Sequence: Flash LEDs to show we are alive
  digitalWrite(PIN_LED_SILICON, HIGH);
  delay(150);
  digitalWrite(PIN_LED_SILICON, LOW);
  digitalWrite(PIN_LED_SOUL, HIGH);
  delay(150);
  digitalWrite(PIN_LED_SOUL, LOW);
}

void loop() {
  // 1. LISTEN FOR COMMANDS (From Python Script or Serial Monitor)
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim(); // Remove whitespace/newlines
    
    if (cmd == "WHO_ARE_YOU?") {
      Serial.println(PLAYER_ID);
    }
    else if (cmd == "CHOOSING") {
      startChoosingAnimation();
    }
    else if (cmd == "RESET") {
      stopChoosingAnimation();
      resetRound();
    }
    else if (cmd == "WIN_SILICON") {
      stopChoosingAnimation();
      triggerRevealEffect("SILICON");
    }
    else if (cmd == "WIN_SOUL") {
      stopChoosingAnimation();
      triggerRevealEffect("SOUL");
    }
  }

  // Choosing animation runs while the game is selecting the track.
  if (choosingAnimation) {
    updateChoosingAnimation();
  }

  // 2. READ BUTTONS (Only if not locked in)
  if (!lockedIn && !choosingAnimation) {
    // Check Silicon (Active LOW)
    if (digitalRead(PIN_BTN_SILICON) == LOW) {
      lockVote("SILICON");
      delay(50); // Debounce
    }
    // Check Soul (Active LOW)
    else if (digitalRead(PIN_BTN_SOUL) == LOW) {
      lockVote("SOUL");
      delay(50); // Debounce
    }
  }
}

// --- HELPER FUNCTIONS ---

void lockVote(String vote) {
  currentVote = vote;
  lockedIn = true; // IMMEDIATE LOCK-IN
  
  // Update LEDs: Turn ON the vote, OFF the other
  if (vote == "SILICON") {
    digitalWrite(PIN_LED_SILICON, HIGH);
    digitalWrite(PIN_LED_SOUL, LOW);
    Serial.println("VOTE:SILICON");
  } 
  else {
    digitalWrite(PIN_LED_SILICON, LOW);
    digitalWrite(PIN_LED_SOUL, HIGH);
    Serial.println("VOTE:SOUL");
  }
}

void resetRound() {
  currentVote = "NONE";
  lockedIn = false;
  // Turn off all lights
  digitalWrite(PIN_LED_SILICON, LOW);
  digitalWrite(PIN_LED_SOUL, LOW);
}

void startChoosingAnimation() {
  choosingAnimation = true;
  choosingSiliconOn = true;
  choosingLastToggleAt = millis();
  // Clear previous vote indication while the roulette/selection is running.
  currentVote = "NONE";
  lockedIn = false;
  digitalWrite(PIN_LED_SILICON, HIGH);
  digitalWrite(PIN_LED_SOUL, LOW);
}

void stopChoosingAnimation() {
  choosingAnimation = false;
  digitalWrite(PIN_LED_SILICON, LOW);
  digitalWrite(PIN_LED_SOUL, LOW);
}

void updateChoosingAnimation() {
  unsigned long now = millis();
  if ((now - choosingLastToggleAt) < CHOOSING_FLICKER_MS) {
    return;
  }
  choosingLastToggleAt = now;
  choosingSiliconOn = !choosingSiliconOn;
  digitalWrite(PIN_LED_SILICON, choosingSiliconOn ? HIGH : LOW);
  digitalWrite(PIN_LED_SOUL, choosingSiliconOn ? LOW : HIGH);
}

void triggerRevealEffect(String correctVote) {
  int correctPin = (correctVote == "SILICON") ? PIN_LED_SILICON : PIN_LED_SOUL;
  int wrongPin = (correctVote == "SILICON") ? PIN_LED_SOUL : PIN_LED_SILICON;

  bool votedCorrect = (currentVote == correctVote);
  bool votedWrong = (currentVote != "NONE") && !votedCorrect;

  // If player was wrong, keep their chosen button solid while the correct one flickers.
  if (votedWrong) {
    if (currentVote == "SILICON") {
      digitalWrite(PIN_LED_SILICON, HIGH);
      digitalWrite(PIN_LED_SOUL, LOW);
    } else {
      digitalWrite(PIN_LED_SILICON, LOW);
      digitalWrite(PIN_LED_SOUL, HIGH);
    }
  } else {
    digitalWrite(PIN_LED_SILICON, LOW);
    digitalWrite(PIN_LED_SOUL, LOW);
  }

  // Flicker correct answer 5 times.
  for(int i=0; i<5; i++) {
    digitalWrite(correctPin, LOW);
    if (votedWrong) digitalWrite(wrongPin, HIGH);
    delay(100);
    digitalWrite(correctPin, HIGH);
    if (votedWrong) digitalWrite(wrongPin, HIGH);
    delay(100);
  }

  // Final light state after reveal.
  if (votedWrong) {
    digitalWrite(correctPin, LOW);
    digitalWrite(wrongPin, HIGH);
  } else {
    digitalWrite(correctPin, HIGH);
    digitalWrite(wrongPin, LOW);
  }
}