#include <stdio.h>
#include <stdlib.h>
#include "btlib.h"
#include <string.h>
#include "MQTTClient.h"
#include "cJSON.h"

#define BROKER_URL "tcp://broker.emqx.io:1883"
#define CLIENTID "AyanPi"
#define TOPIC "CSC2006"
#define QOS 1
#define TIMEOUT 10000L



int mesh_callback(int clientnode,char *data,int datlen);


int main()
  {

    if(init_blue("devices.txt") == 0)
      return(0);
    // MESH SERVER
    mesh_server(mesh_callback);

  }

int mesh_callback(int clientnode,char *data,int datlen)
  {
  int n;
  printf("Mesh packet from %s\n",device_name(clientnode));
  char *delimiter = strchr(data,':');
  if (delimiter != NULL){
        //extract scope name
        char node[32];
		memcpy(node,data,delimiter-data);
        node[delimiter-data] = '\0';
        printf("%s\n",node);
        
        //Extract RSSI
        char rssi[32];
        strcpy(rssi,delimiter+1);
        printf("%s\n",rssi);
   
        //begin MQTT
        MQTTClient client;
        MQTTClient_connectOptions conn_opts = MQTTClient_connectOptions_initial>
        MQTTClient_message pubmsg = MQTTClient_message_initializer;
        MQTTClient_deliveryToken token;
        int rc;
        
        //int rssi = (int)(*rssi_char);
        //int node = (int)(*name);
        printf("sending rssi: %s\n",rssi);
        printf("sending node: %s\n",node);
        cJSON* root = cJSON_CreateObject();
        cJSON_AddStringToObject(root, "node", node);
        cJSON_AddStringToObject(root, "rssi", rssi);
        char* json_str = cJSON_Print(root);
		//Connect to MQTT Broker
        MQTTClient_create(&client, BROKER_URL, CLIENTID, MQTTCLIENT_PERSISTENCE>
        conn_opts.keepAliveInterval = 20;
        conn_opts.cleansession = 1;
        if ((rc = MQTTClient_connect(client, &conn_opts)) != MQTTCLIENT_SUCCESS>
                printf("Failed to connect to MQTT broker, return code %d\n",rc);
                exit(EXIT_FAILURE);
        }
        //Publish Message to topic
        pubmsg.payload = json_str;
        pubmsg.payloadlen = strlen(json_str);
        pubmsg.qos = QOS;
        pubmsg.retained = 0;
        MQTTClient_publishMessage(client, TOPIC, &pubmsg, &token);
        printf("Message with token value %d sent to topic %s\n", token, TOPIC);
        MQTTClient_waitForCompletion(client, token, TIMEOUT);
        printf("Disconnecting from MQTT");
        //Disconnect from MQTT broker
        MQTTClient_disconnect(client, 10000);
        MQTTClient_destroy(&client);
  }
  //~ for(n = 0 ; n < datlen ; ++n)
    //~ printf("%c",data[n]);
  //~ printf("\n");

  //~ printf("data: %s\n", data);

  //~ if(data[0] == 'D')   // 'D' programmed as exit command
    //~ return(SERVER_EXIT);
  return(SERVER_CONTINUE);  // wait for another packet
  }
