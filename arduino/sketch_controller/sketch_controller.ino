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
    else if (cmd == "RESET") {
      resetRound();
    }
    else if (cmd == "WIN_SILICON") {
       if (currentVote == "SILICON") triggerWinEffect(PIN_LED_SILICON);
    }
    else if (cmd == "WIN_SOUL") {
       if (currentVote == "SOUL") triggerWinEffect(PIN_LED_SOUL);
    }
  }

  // 2. READ BUTTONS (Only if not locked in)
  if (!lockedIn) {
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

void triggerWinEffect(int pin) {
  // Flash the winner 5 times
  for(int i=0; i<5; i++) {
    digitalWrite(pin, LOW);
    delay(100);
    digitalWrite(pin, HIGH);
    delay(100);
  }
  digitalWrite(pin, HIGH); // Keep it on for glory
}