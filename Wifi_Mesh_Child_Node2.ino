#include "painlessMesh.h"
#include <M5StickCPlus.h>
#include <WiFi.h>
#include <Arduino_JSON.h>

#define MESH_PREFIX "PA01_MESH"
#define MESH_PASSWORD "12345678"
#define MESH_PORT 5555

Scheduler userScheduler; // to control your personal task
painlessMesh mesh;
bool wifiScanRunning = false;
//Target SSID
const char* targetSSID = "Xiaomi_109C";
int rssi = -100;
int nodeNumber = 2;

//String to send to other nodes with rssi readings
String message;

// User stub
void sendMessage() ; // Prototype so PlatformIO doesn't complain

Task taskSendMessage(TASK_SECOND * 1, TASK_FOREVER, &sendMessage);
Task taskScanWifi(TASK_SECOND * 10, TASK_FOREVER, [](){
  wifiScanRunning = true;
  int numNetworks = WiFi.scanNetworks();
  for (int i = 0; i < numNetworks; i++) {
    String ssid = WiFi.SSID(i);
    if (ssid == targetSSID) {
      rssi = WiFi.RSSI(i);
      Serial.print(ssid);
      Serial.print(" RSSI: ");
      Serial.println(rssi);
    }
  }
  wifiScanRunning = false;
});

void sendMessage() {
  String msg = "node2:";
  msg += rssi;
  mesh.sendBroadcast(msg);
  taskSendMessage.setInterval(random(TASK_SECOND * 3, TASK_SECOND * 9));
}

// Needed for painless library
void receivedCallback(uint32_t from, String &msg) {
  Serial.printf("Received from %u msg= %s\n", from, msg.c_str());

}


void newConnectionCallback(uint32_t nodeId) {
  Serial.printf("--> startHere: New Connection, nodeId = %u\n", nodeId);
}

void changedConnectionCallback() {
  Serial.printf("Changed connections\n");
}

void nodeTimeAdjustedCallback(int32_t offset) {
  Serial.printf("Adjusted time %u. Offset = %d\n", mesh.getNodeTime(), offset);
}

void setup() {
  Serial.begin(115200);
  M5.begin();

  //mesh.setDebugMsgTypes( ERROR | MESH_STATUS | CONNECTION | SYNC | COMMUNICATION | GENERAL | MSG_TYPES | REMOTE ); // all types on
  mesh.setDebugMsgTypes( ERROR | STARTUP | CONNECTION | MESH_STATUS);  // set before init() so that you can see startup message

  mesh.init(MESH_PREFIX, MESH_PASSWORD, &userScheduler, MESH_PORT);
  mesh.onReceive(&receivedCallback);
  mesh.onNewConnection(&newConnectionCallback);
  mesh.onChangedConnections(&changedConnectionCallback);
  mesh.onNodeTimeAdjusted(&nodeTimeAdjustedCallback);
  mesh.setRoot(false);
  mesh.setContainsRoot(true);
  M5.Lcd.setRotation(3);
  M5.Lcd.fillScreen(BLACK);
  M5.Lcd.setCursor(0, 0, 2);
  M5.Lcd.print("WIFI child Start");
  M5.Lcd.setCursor(0, 40, 2);
  M5.Lcd.print("Node 2");
  userScheduler.addTask(taskSendMessage);
  userScheduler.addTask(taskScanWifi);
  taskSendMessage.enable();
  taskScanWifi.enable();
}

void loop() {
  
  if (!wifiScanRunning) {
    mesh.update();
  }
}
