from __future__ import print_function
# -*- coding: utf-8 -

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
import uuid
import numpy as np
from sklearn.preprocessing import normalize
from collections import namedtuple

EntityInfo = namedtuple('EntityInfo', 'x, y, z, name')

# Create one agent host for parsing:
agent_hosts = [MalmoPython.AgentHost()]

# Parse the command-line options:
agent_hosts[0].addOptionalFlag("debug,d", "Display debug information.")
agent_hosts[0].addOptionalIntArgument("agents,n", "Number of agents to use.", 2)

try:
    agent_hosts[0].parse(sys.argv)
except RuntimeError as e:
    print('ERROR:', e)
    print(agent_hosts[0].getUsage())
    exit(1)
if agent_hosts[0].receivedArgument("help"):
    print(agent_hosts[0].getUsage())
    exit(0)

DEBUG = agent_hosts[0].receivedArgument("debug")
NUM_AGENTS = agent_hosts[0].getIntArgument("agents")

agent_hosts += [MalmoPython.AgentHost() for x in range(1, NUM_AGENTS)]

# Set up debug output:
for ah in agent_hosts:
    ah.setDebugOutput(DEBUG) # Turn client-pool connection messages on/off.

if sys.version_info[0] == 2:
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0) # flush print output immediately
else:
    import functools
    print = functools.partial(print, flush = True)

def safeStartMission(agent_host, mission, client_pool, mission_record, role, expId):
    used_attempts = 0
    max_attempts = 5
    print("Calling startMission for role", role)
    while True:
        try:
            # Attempt start:
            agent_host.startMission(mission, client_pool, mission_record, role, expId)
            break
        except MalmoPython.MissionException as e:
            errorCode = e.details.errorCode
            if errorCode == MalmoPython.MissionErrorCode.MISSION_SERVER_WARMING_UP:
                print("Server not quite ready yet - waiting...")
                time.sleep(2)
            elif errorCode == MalmoPython.MissionErrorCode.MISSION_INSUFFICIENT_CLIENTS_AVAILABLE:
                print("Not enough available Minecraft instances running.")
                used_attempts += 1
                if used_attempts < max_attempts:
                    print("Will wait in case they are starting up.", max_attempts - used_attempts, "attempts left.")
                    time.sleep(2)
            elif errorCode == MalmoPython.MissionErrorCode.MISSION_SERVER_NOT_FOUND:
                print("Server not found - has the mission with role 0 been started yet?")
                used_attempts += 1
                if used_attempts < max_attempts:
                    print("Will wait and retry.", max_attempts - used_attempts, "attempts left.")
                    time.sleep(2)
            else:
                print("Other error:", e.message)
                print("Waiting will not help here - bailing immediately.")
                exit(1)
        if used_attempts == max_attempts:
            print("All chances used up - bailing now.")
            exit(1)
    print("startMission called okay.")

def safeWaitForStart(agent_hosts):
    print("Waiting for the mission to start", end=' ')
    start_flags = [False for a in agent_hosts]
    start_time = time.time()
    time_out = 120  # Allow a two minute timeout.
    while not all(start_flags) and time.time() - start_time < time_out:
        states = [a.peekWorldState() for a in agent_hosts]
        start_flags = [w.has_mission_begun for w in states]
        errors = [e for w in states for e in w.errors]
        if len(errors) > 0:
            print("Errors waiting for mission start:")
            for e in errors:
                print(e.text)
            print("Bailing now.")
            exit(1)
        time.sleep(0.1)
        print(".", end=' ')
    if time.time() - start_time >= time_out:
        print("Timed out while waiting for mission to start - bailing.")
        exit(1)
    print()
    print("Mission has started.")

def getXML(x, y, z):
    xml = '''<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
            <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            
              <About>
                <Summary>Simple chasing agent</Summary>
              </About>

              <ModSettings>
                <MsPerTick>50</MsPerTick>
              </ModSettings>
              
              <ServerSection>
                <ServerInitialConditions>
                  <Time>
                    <StartTime>12000</StartTime>
                    <AllowPassageOfTime>false</AllowPassageOfTime>
                  </Time>
                  <Weather>clear</Weather>
                </ServerInitialConditions>
                <ServerHandlers>
                  <FlatWorldGenerator destroyAfterUse="true" forceReset="true"/>
                  <DrawingDecorator>
                    <!-- Outer wall -->
                    <DrawCuboid x1="0" y1="4" z1="0" x2="30" y2="6" z2="40" type="brick_block"/>
                    <DrawCuboid x1="1" y1="4" z1="1" x2="29" y2="7" z2="39" type="air"/>

                    <!-- 1 -->
                    <DrawCuboid x1="10" y1="4" z1="10" x2="20" y2="6" z2="15" type="brick_block"/>
                    <DrawCuboid x1="13" y1="4" z1="13" x2="17" y2="6" z2="15" type="air"/>

                    <!-- 2 -->
                    <DrawCuboid x1="1" y1="4" z1="10" x2="5" y2="6" z2="15" type="brick_block"/>
                    <DrawLine x1="5" y1="4" z1="15" x2="1" y2="4" z2="19" type="brick_block"/>
                    <DrawLine x1="5" y1="5" z1="15" x2="1" y2="5" z2="19" type="brick_block"/>
                    <DrawLine x1="5" y1="6" z1="15" x2="1" y2="6" z2="19" type="brick_block"/>
                    <DrawBlock x="1" y="6" z="16" type="brick_block"/>
                    <DrawBlock x="2" y="6" z="16" type="brick_block"/>
                    <DrawBlock x="1" y="6" z="17" type="brick_block"/>

                    <!-- 3 -->
                    <DrawCuboid x1="29" y1="4" z1="10" x2="25" y2="6" z2="15" type="brick_block"/>
                    <DrawLine x1="25" y1="4" z1="15" x2="29" y2="4" z2="19" type="brick_block"/>
                    <DrawLine x1="25" y1="5" z1="15" x2="29" y2="5" z2="19" type="brick_block"/>
                    <DrawLine x1="25" y1="6" z1="15" x2="29" y2="6" z2="19" type="brick_block"/>
                    <DrawBlock x="29" y="6" z="16" type="brick_block"/>
                    <DrawBlock x="28" y="6" z="16" type="brick_block"/>
                    <DrawBlock x="29" y="6" z="17" type="brick_block"/>

                    <!-- 4 -->
                    <DrawCuboid x1="20" y1="4" z1="20" x2="18" y2="6" z2="35" type="brick_block"/>
                    <DrawLine x1="20" y1="4" z1="20" x2="25" y2="4" z2="25" type="brick_block"/>
                    <DrawLine x1="20" y1="5" z1="20" x2="25" y2="5" z2="25" type="brick_block"/>
                    <DrawLine x1="20" y1="6" z1="20" x2="25" y2="6" z2="25" type="brick_block"/>
                    <DrawLine x1="25" y1="4" z1="25" x2="20" y2="4" z2="25" type="brick_block"/>
                    <DrawLine x1="25" y1="5" z1="25" x2="20" y2="5" z2="25" type="brick_block"/>
                    <DrawLine x1="25" y1="6" z1="25" x2="20" y2="6" z2="25" type="brick_block"/>
                    <DrawLine x1="25" y1="6" z1="24" x2="20" y2="6" z2="24" type="brick_block"/>
                    <DrawLine x1="24" y1="6" z1="23" x2="20" y2="6" z2="23" type="brick_block"/>
                    <DrawBlock x="21" y="6" z="22" type="brick_block"/>

                    <!-- 5 -->
                    <DrawCuboid x1="10" y1="4" z1="20" x2="12" y2="6" z2="30" type="brick_block"/>
                    <DrawLine x1="10" y1="4" z1="20" x2="5" y2="4" z2="25" type="brick_block"/>
                    <DrawLine x1="10" y1="5" z1="20" x2="5" y2="5" z2="25" type="brick_block"/>
                    <DrawLine x1="10" y1="6" z1="20" x2="5" y2="6" z2="25" type="brick_block"/>
                    <DrawLine x1="5" y1="4" z1="25" x2="10" y2="4" z2="25" type="brick_block"/>
                    <DrawLine x1="5" y1="5" z1="25" x2="10" y2="5" z2="25" type="brick_block"/>
                    <DrawLine x1="5" y1="6" z1="25" x2="10" y2="6" z2="25" type="brick_block"/>
                    <DrawLine x1="5" y1="6" z1="24" x2="10" y2="6" z2="24" type="brick_block"/>
                    <DrawLine x1="6" y1="6" z1="23" x2="10" y2="6" z2="23" type="brick_block"/>
                    <DrawBlock x="9" y="6" z="22" type="brick_block"/>

                    <!-- 6 -->
                    <DrawCuboid x1="29" y1="4" z1="30" x2="25" y2="6" z2="35" type="brick_block"/>

                    <!-- 7 -->
                    <DrawCuboid x1="13" y1="4" z1="35" x2="13" y2="6" z2="40" type="brick_block"/>
                    <DrawCuboid x1="13" y1="4" z1="35" x2="5" y2="6" z2="35" type="brick_block"/>
                    <DrawCuboid x1="5" y1="4" z1="30" x2="1" y2="6" z2="30" type="brick_block"/>

                    <DrawBlock x="15" y="3" z="1" type="diamond_block"/>

                    <!-- A --> <DrawBlock x="8" y="3" z="8" type="gold_block"/>
                    <!-- B --> <DrawBlock x="22" y="3" z="8" type="gold_block"/>
                    <!-- C --> <DrawBlock x="15" y="3" z="13" type="gold_block"/>
                    <!-- D --> <DrawBlock x="7" y="3" z="18" type="gold_block"/>
                    <!-- E --> <DrawBlock x="15" y="3" z="18" type="gold_block"/>
                    <!-- F --> <DrawBlock x="23" y="3" z="18" type="gold_block"/>
                    <!-- G --> <DrawBlock x="28" y="3" z="25" type="gold_block"/>
                    <!-- H --> <DrawBlock x="23" y="3" z="28" type="gold_block"/>
                    <!-- I --> <DrawBlock x="7" y="3" z="28" type="gold_block"/>
                    <!-- J --> <DrawBlock x="2" y="3" z="25" type="gold_block"/>
                    <!-- K --> <DrawBlock x="15" y="3" z="32" type="gold_block"/>
                    <!-- L --> <DrawBlock x="7" y="3" z="32" type="gold_block"/>
                    <!-- M --> <DrawBlock x="28" y="3" z="38" type="gold_block"/>
                    <!-- N --> <DrawBlock x="23" y="3" z="38" type="gold_block"/>
                    <!-- O --> <DrawBlock x="18" y="3" z="38" type="gold_block"/>
                    <!-- P --> <DrawBlock x="8" y="3" z="38" type="gold_block"/>
                    <!-- Q --> <DrawBlock x="2" y="3" z="35" type="gold_block"/>
                  </DrawingDecorator>
                  <!--ServerQuitFromTimeUp description="DIDNT_CATCH" timeLimitMs="30000"/-->
                  <ServerQuitWhenAnyAgentFinishes/>
                </ServerHandlers>
              </ServerSection>
              
              <AgentSection mode="Survival">
                <Name>Seeker</Name>
                <AgentStart>
                  <Placement x="15.5" y="5.0" z="1.5" yaw="0"/>
                </AgentStart>
                <AgentHandlers>
                  <ObservationFromFullStats/>
                  <ObservationFromNearbyEntities>
                    <Range name="entities" xrange="40" yrange="40" zrange="40"/>
                  </ObservationFromNearbyEntities>
                  <RewardForCollectingItem>
                    <Item type="diamond" reward="50"/>
                  </RewardForCollectingItem>
                  <AgentQuitFromCollectingItem>
                    <Item type="diamond" description="CATCH" />
                  </AgentQuitFromCollectingItem>
                  <ContinuousMovementCommands turnSpeedDegs="840"/>
                  <InventoryCommands/>
                </AgentHandlers>
              </AgentSection>

              <AgentSection mode="Survival">
                <Name>Runner</Name>
                <AgentStart>
                  <Placement x="''' + str(x) + '''" y="5.0" z="''' + str(z) + '''" yaw="0"/>
                    <Inventory>
                        <InventoryItem slot="0" type="diamond"/>
                    </Inventory>
                </AgentStart>
                <AgentHandlers>
                  <ObservationFromFullStats/>
                  <ObservationFromNearbyEntities>
                    <Range name="entities" xrange="40" yrange="40" zrange="40"/>
                  </ObservationFromNearbyEntities>
                  <RewardForDiscardingItem>
                    <Item type="diamond" reward="-50"/>
                  </RewardForDiscardingItem>
                  <ContinuousMovementCommands turnSpeedDegs="840"/>
                  <InventoryCommands/>
                </AgentHandlers>
              </AgentSection>
            </Mission>'''

    return xml

vgi = ['0', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 
    'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q']

vg = {
    '0': (15.5, 3, 1.5),
    'A': (22.5, 3, 8.5),
    'B': (8.5, 3, 8.5),
    'C': (15.5, 3, 13.5),
    'D': (23.5, 3, 18.5),
    'E': (15.5, 3, 18.5),
    'F': (7.5, 3, 18.5),
    'G': (28.5, 3, 25.5),
    'H': (23.5, 3, 28.5),
    'I': (7.5, 3, 28.5),
    'J': (2.5, 3, 25.5),
    'K': (15.5, 3, 32.5),
    'L': (7.5, 3, 32.5),
    'M': (28.5, 3, 38.5),
    'N': (23.5, 3, 38.5),
    'O': (18.5, 3, 38.5),
    'P': (8.5, 3, 38.5),
    'Q': (2.5, 3, 35.5),
}

edges = {
    '0': {'A', 'B'},
    'A': {'0', 'B', 'D'},
    'B': {'0', 'A', 'F'},
    'C': {'E'},
    'D': {'A', 'E', 'G'},
    'E': {'C', 'D', 'F', 'K'},
    'F': {'B', 'E', 'J'},
    'G': {'D', 'H'},
    'H': {'G', 'N'},
    'I': {'J', 'L'},
    'J': {'F', 'I'},
    'K': {'E', 'L', 'O'},
    'L': {'I', 'K', 'Q'},
    'M': {'N'},
    'N': {'H', 'M', 'O'},
    'O': {'K', 'N'},
    'P': {'Q'},
    'Q': {'L', 'P'}
}

can_see = {
    '0': {'0', 'A', 'B'},
    'A': {'A', '0', 'B', 'D'},
    'B': {'B', '0', 'A', 'F'},
    'C': {'C', 'E', 'K'},
    'D': {'D', 'A', 'E', 'G', 'F'},
    'E': {'E', 'C', 'D', 'F', 'K'},
    'F': {'F', 'B', 'E', 'J', 'D'},
    'G': {'G', 'D', 'H'},
    'H': {'H', 'G', 'N'},
    'I': {'I', 'J', 'L'},
    'J': {'J', 'F', 'I'},
    'K': {'K', 'E', 'L', 'O', 'Q'},
    'L': {'L', 'I', 'K', 'Q'},
    'M': {'M', 'N', 'O'},
    'N': {'N', 'H', 'M', 'O'},
    'O': {'O', 'K', 'N', 'M'},
    'P': {'P', 'Q'},
    'Q': {'Q', 'L', 'P', 'K'}
}

# Set up a client pool
client_pool = MalmoPython.ClientPool()
for x in range(10000, 10000 + NUM_AGENTS):
    client_pool.add(MalmoPython.ClientInfo('127.0.0.1', x))

runner_pos = random.choice(vgi[11:])
my_mission = MalmoPython.MissionSpec(getXML(*vg[runner_pos]), True)
my_mission_record = MalmoPython.MissionRecordSpec()

expID = str(uuid.uuid4())

for i in range(len(agent_hosts)):
    agent_hosts[i].setRewardsPolicy(MalmoPython.RewardsPolicy.KEEP_ALL_REWARDS)
    safeStartMission(agent_hosts[i], my_mission, client_pool, my_mission_record, i, expID)

safeWaitForStart(agent_hosts)

def calcYawTo(fx, fy, fz, x, y, z):
    dx = fx - x
    dz = fz - z

    return -180 * math.atan2(dx, dz) / math.pi

def distance(x1, y1, z1, x2, y2, z2):
    return abs(x1 - x2) + abs(z1 - z2)

class HiddenMarkovModel:
    def __init__(self, f0, T):
        self.f = f0
        self.T = T

    def get(self):
        return np.array(self.f.T)

    def tick(self, O):
        self.f = O * self.T.T * self.f
        self.f /= sum(self.f)

        return np.array(self.f.T)

class Agent:
    def __init__(self, agent_host, starting_pos = '0'):
        self.agent_host = agent_host

        self.current = starting_pos
        self.going_to = starting_pos

        self.speed = 1

        f0 = np.matrix([1/18] * 18).T
        T = np.matrix([[4.3 / distance(*vg[vgi[i]], *vg[vgi[j]]) 
                if vgi[j] in edges[vgi[i]] else 0 
                for j in range(0, 18)]
            for i in range(0, 18)]).clip(0, 1)

        for i in range(0, 18):
            T[i, i] = 1 - (T[i].sum() / len(edges[vgi[i]]))

            T[i] = normalize(np.matrix(T[i]), norm='l1')[0]

        self.hmm = HiddenMarkovModel(f0, T)

    def update(self, obs):
        self.pitch = obs['Pitch']
        self.yaw = obs['Yaw']
        self.pos = (obs['XPos'], obs['YPos'], obs['ZPos'])
        self.life = obs['Life']

    def do(self, command):
        self.agent_host.sendCommand(command)

    def go_to(self, node):
        self.going_to = node

    def get_next(self, avoid = []):
        try:
            return random.choice(list(edges[self.going_to] - set(avoid)))
        except:
            return random.choice(list(edges[self.going_to]))

    def loop(self):
        if self.pitch < 0:
            self.do("pitch 0")

        yaw_to_next = calcYawTo(*vg[self.going_to], *self.pos)

        # Find shortest angular distance between the two yaws, preserving sign:
        deltaYaw = yaw_to_next - self.yaw

        while deltaYaw < -180: deltaYaw += 360;
        while deltaYaw > 180: deltaYaw -= 360;

        deltaYaw /= 180.0;

        # And turn:
        self.do("turn " + str(deltaYaw))

        dist = distance(*self.pos, *vg[self.going_to])

        if dist > 1.8:
            agent.sendCommand("move %d" % self.speed)
        else:
            agent.sendCommand("move 0")

            self.current, self.going_to = self.going_to, self.get_next([self.current])

class Seeker(Agent):
    def get_next(self, avoid = []):
        O = np.diag([1] * 18)

        f = self.hmm.tick(O)

        neighbors_index = set(range(0, 18))
        neighbors_index -= set(map(lambda x: vgi.index(x), list(edges[self.going_to])))
        neighbors_index -= set(map(lambda x: vgi.index(x), avoid))

        for i in neighbors_index:
            f[0, i] = 0

        f = list(normalize(f, norm='l1')[0])

        chosen = vgi[np.random.choice(range(0, 18), p = f)]

        return chosen

class Runner(Agent):
    def get_next(self, avoid = []):
        O = np.diag([1] * 18)

        f = 1 / self.hmm.tick(O)

        neighbors_index = set(range(0, 18))
        neighbors_index -= set(map(lambda x: vgi.index(x), list(edges[self.going_to])))
        neighbors_index -= set(map(lambda x: vgi.index(x), avoid))

        for i in neighbors_index:
            f[0, i] = 0

        f = normalize(f, norm='l1')

        chosen = vgi[np.random.choice(range(0, 18), p = f[0])]

        return chosen

time.sleep(1)

running = True
current_obs = [{} for x in range(NUM_AGENTS)]
unresponsive_count = [10 for x in range(NUM_AGENTS)]
num_responsive_agents = lambda: sum([urc > 0 for urc in unresponsive_count])

seeker = Seeker(agent_hosts[0], '0')
runner = Runner(agent_hosts[1], runner_pos)

timed_out = False

yaw_to_mob = 0

try:
    while num_responsive_agents() > 0 and not timed_out:
        for i in range(NUM_AGENTS):
            agent = agent_hosts[i]

            world_state = agent.getWorldState()

            if world_state.is_mission_running == False:
                timed_out = True
            elif world_state.number_of_observations_since_last_state > 0:
                unresponsive_count[i] = 10

                obvsText = world_state.observations[-1].text
                data = json.loads(obvsText)
                current_obs[i] = data

            if agent == seeker.agent_host:
                seeker.update(current_obs[0])
                seeker.loop()
            elif agent == runner.agent_host:
                runner.update(current_obs[1])
                runner.loop()
except KeyboardInterrupt:
    pass

# mission has ended.
print("Mission over")
reward = list(map(lambda r: r.getValue(), world_state.rewards))
print("Result: " + str(reward))
exit(0)
