#include "painlessMesh.h"
#include <M5StickCPlus.h>
#include <WiFi.h>
#include <Arduino_JSON.h>
#include <PubSubClient.h>
#include <WiFiClient.h>

#define MESH_PREFIX "PA01_MESH"
#define MESH_PASSWORD "12345678"
#define MESH_PORT 5555
#define MAX_SIZE 4
#define MQTT_SERVER "broker.emqx.io"
#define MQTT_PORT 1883

#define STATION_SSID "Whatsup"
#define STATION_PASSWORD "12345678"

#define HOSTNAME "MQTT_Bridge"

void mqttCallback(char* topic, byte* payload, unsigned int length);
IPAddress getlocalIP();

IPAddress myIP(0,0,0,0);
IPAddress mqttBroker(192,168,31,113);


Scheduler userScheduler; // to control your personal task
painlessMesh mesh;
WiFiClient wifiClient;
PubSubClient mqttClient("broker.emqx.io", 1883, wifiClient);



bool wifiScanRunning = false;
//Target SSID
const char* targetSSID = "Whatsup";
int rssi = -100;
int nodeNumber = 0;
int retryCount = 0; // counter for number of retries
unsigned long lastRetryTime = 0; // timestamp of last retry attempt
const int MAX_RETRIES = 3; // maximum number of retry attempts


int node_list[MAX_SIZE];
String message_list[MAX_SIZE];
int num_elements = 0;

// MQTT broker information
//const char* broker = "broker.emqx.io";
const int port = 1883;
const char* topic = "CSC2006";

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
  JSONVar jsonReadings;
  jsonReadings["node"] = nodeNumber;
  jsonReadings["rssi"] = rssi;
  String msg = JSON.stringify(jsonReadings);
  bool success = mesh.sendBroadcast(msg,true);
  if (!success) { // if message failed to send
    if (retryCount < MAX_RETRIES) { // if we haven't exceeded the maximum number of retries
      unsigned long currentTime = millis();
      if (currentTime - lastRetryTime >= 3000) { // if timeout period has elapsed
        mesh.update(); // call update() to ensure message queue is processed
        success = mesh.sendBroadcast(msg,true); // attempt to resend message
        lastRetryTime = currentTime; // update retry timestamp
        retryCount++; // increment retry counter
      }
    } else { // if exceeded the maximum number of retries
      Serial.println("Error: message transmission failed after multiple attempts");
      retryCount = 0; // reset retry counter
    }
  } else { // if message was successfully sent
    retryCount = 0; // reset retry counter
  }
  taskSendMessage.setInterval(random(TASK_SECOND * 3, TASK_SECOND * 6));
}

// Needed for painless library
void receivedCallback(uint32_t from, String &msg) {
  Serial.printf("Received from %u msg=%s\n", from, msg.c_str());
  bool mqtt_success = mqttClient.publish(topic, msg.c_str());
  if (mqtt_success) {
    Serial.println("publish success");
  } else {
    Serial.println("publish fail");
  }
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
  WiFi.mode(WIFI_STA);


  //mesh.setDebugMsgTypes( ERROR | MESH_STATUS | CONNECTION | SYNC | COMMUNICATION | GENERAL | MSG_TYPES | REMOTE ); // all types on
  mesh.setDebugMsgTypes( ERROR | STARTUP | CONNECTION );  // set before init() so that you can see startup message
  mesh.init(MESH_PREFIX, MESH_PASSWORD, &userScheduler, MESH_PORT);
  mesh.onReceive(&receivedCallback);
  mesh.stationManual(STATION_SSID, STATION_PASSWORD);
  mesh.setHostname(HOSTNAME);
  mesh.onNewConnection(&newConnectionCallback);
  mesh.onChangedConnections(&changedConnectionCallback);
  mesh.onNodeTimeAdjusted(&nodeTimeAdjustedCallback);
  mesh.setRoot(true);
  mesh.setContainsRoot(true);
  mqttClient.setServer("broker.emqx.io", 1883);
  mqttClient.setKeepAlive(60);
  M5.Lcd.setRotation(3);
  M5.Lcd.fillScreen(BLACK);
  M5.Lcd.setCursor(0, 0, 2);
  M5.Lcd.print("WIFI root Start");
  M5.Lcd.setCursor(0, 40, 2);
  M5.Lcd.print("Node 0");
  userScheduler.addTask(taskSendMessage);
  userScheduler.addTask(taskScanWifi);
  taskSendMessage.enable();
  taskScanWifi.enable();
}

void loop() {
  mesh.update();
  mqttClient.loop();
  if(myIP != getlocalIP()){
    myIP = getlocalIP();
    Serial.println("My IP is " + myIP.toString());
    M5.Lcd.setCursor(0, 20, 2);
    M5.Lcd.print("IP: ");
    M5.Lcd.println(getlocalIP());
    if (mqttClient.connect("painlessMeshClient")) {
      mqttClient.publish(topic,"Ready!");
    } 
  }
}


IPAddress getlocalIP() {
  return IPAddress(mesh.getStationIP());
}



