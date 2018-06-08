from __future__ import print_function
# -*- coding: utf-8 -

# ------------------------------------------------------------------------------------------------
# Copyright (c) 2016 Microsoft Corporation
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
# associated documentation files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge, publish, distribute,
# sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
# NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# ------------------------------------------------------------------------------------------------

# Silly test of:
#   Minecart track shaping
#   Entity drawing
#   Step shaping
#
# If everything is working correctly, the agent should ride around happily forever.

from builtins import range
import MalmoPython
import os
import random
import sys
import time
import json
import random
import re
import math

# For a bit more fun, set MOB_TYPE = "Creeper"...
MOB_TYPE = "Villager"

def calcYawToMob(entities, x, y, z):
    ''' Find the mob we are following, and calculate the yaw we need in order to face it '''
    for ent in entities:
        if ent['name'] == MOB_TYPE:
            dx = ent['x'] - x
            dz = ent['z'] - z
            yaw = -180 * math.atan2(dx, dz) / math.pi
            return yaw
    return 0

agent_host = MalmoPython.AgentHost()
try:
    agent_host.parse(sys.argv)
except RuntimeError as e:
    print('ERROR:', e)
    print(agent_host.getUsage())
    exit(1)
if agent_host.receivedArgument("help"):
    print(agent_host.getUsage())
    exit(0)

endCondition = ""
timeoutCondition = ""
if agent_host.receivedArgument("test"):
    timeoutCondition = '<ServerQuitFromTimeUp timeLimitMs="240000" description="FAILED"/>'
    endCondition = '''<AgentQuitFromCollectingItem>
                        <Item type="diamond" description="PASSED"/>
                      </AgentQuitFromCollectingItem>'''

missionXML='''<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
            <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            
              <About>
                <Summary>Simple chasing agent</Summary>
              </About>

              <ModSettings>
                <MsPerTick>20</MsPerTick>
              </ModSettings>
              
              <ServerSection>
                <ServerInitialConditions>
                  <Time>
                    <StartTime>12000</StartTime>
                    <AllowPassageOfTime>false</AllowPassageOfTime>
                  </Time>
                  <!--Weather>rain</Weather-->
                </ServerInitialConditions>
                <ServerHandlers>
                  <FlatWorldGenerator destroyAfterUse="true" forceReset="true"/>
                  <DrawingDecorator>
                    <DrawSphere x="-27" y="70" z="0" radius="30" type="air"/>

                    <DrawEntity x="20.5" y="5.0" z="16.5" type="''' + MOB_TYPE + '''"/>
                  </DrawingDecorator>
                  <!--ServerQuitFromTimeUp timeLimitMs="30000"/-->
                  <ServerQuitWhenAnyAgentFinishes/>
                </ServerHandlers>
              </ServerSection>
              
              <AgentSection mode="Survival">
                <Name>Seeker</Name>
                <AgentStart>
                  <Placement x="18.5" y="5.0" z="20.5" yaw="270"/>
                    <Inventory>
                        <InventoryItem slot="8" type="diamond_sword"/>
                    </Inventory>
                </AgentStart>
                <AgentHandlers>
                  <ObservationFromFullStats/>
                  <ObservationFromNearbyEntities>
                    <Range name="entities" xrange="40" yrange="40" zrange="40"/>
                  </ObservationFromNearbyEntities>
                  <RewardForMissionEnd rewardForDeath="-100.0">
                    <Reward description="PASSED" reward="100.0"/>
                    <Reward description="FAILED" reward="-100.0"/>
                  </RewardForMissionEnd>
                  <ContinuousMovementCommands/>
                </AgentHandlers>
              </AgentSection>
            </Mission>'''

if sys.version_info[0] == 2:
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # flush print output immediately
else:
    import functools
    print = functools.partial(print, flush=True)
my_mission = MalmoPython.MissionSpec(missionXML,True)

my_mission_record = MalmoPython.MissionRecordSpec()
max_retries = 3
for retry in range(max_retries):
    try:
        agent_host.startMission( my_mission, my_mission_record )
        break
    except RuntimeError as e:
        if retry == max_retries - 1:
            print("Error starting mission",e)
            print("Is the game running?")
            exit(1)
        else:
            time.sleep(2)

world_state = agent_host.getWorldState()
while not world_state.has_mission_begun:
    time.sleep(0.1)
    world_state = agent_host.getWorldState()

'''agent_host.sendCommand("use 1")     # Click on the minecart...
agent_host.sendCommand("use 0")
agent_host.sendCommand("move 1")    # And start moving forward...
agent_host.sendCommand("pitch -0.1")    # Look up'''

def distance(x1, y1, x2, y2):
    return abs(x1 - x2) + abs(y1 - y2)

def look_at(yaw, target_yaw):
    pass

yaw_to_mob = 0
turn_key = ""

while world_state.is_mission_running:
    world_state = agent_host.getWorldState()

    if world_state.number_of_observations_since_last_state > 0:
        obvsText = world_state.observations[-1].text
        data = json.loads(obvsText) # observation comes in as a JSON string...

        current_x = data.get(u'XPos', 0)
        current_z = data.get(u'ZPos', 0)
        current_y = data.get(u'YPos', 0)
        yaw = data.get(u'Yaw', 0)
        pitch = data.get(u'Pitch', 0)
        
        # Try to look somewhere interesting:
        if "entities" in data:
            yaw_to_mob = calcYawToMob(data['entities'], current_x, current_y, current_z)
            for entity in data['entities']:
                if entity['name'] == 'Villager':
                    xm, ym = entity['x'], entity['z']
        if pitch < 0:
            agent_host.sendCommand("pitch 0") # stop looking up
        # Find shortest angular distance between the two yaws, preserving sign:
        deltaYaw = yaw_to_mob - yaw
        while deltaYaw < -180:
            deltaYaw += 360;
        while deltaYaw > 180:
            deltaYaw -= 360;
        deltaYaw /= 180.0;
        # And turn:
        agent_host.sendCommand("turn " + str(deltaYaw))

        dist = distance(current_x, current_z, xm, ym)

        if dist > 5:
            agent_host.sendCommand("move 1")
        else:
            agent_host.sendCommand("move 0")

# mission has ended.
print("Mission over")
reward = world_state.rewards[-1].getValue()
print("Result: " + str(reward))
if reward < 0:
    exit(1)
else:
    exit(0)
