from pathlib import Path

import gym
import numpy as np
from scipy import rand
#from sympy import Q
import pygame
from gym.spaces import Box, Discrete


# As in Yang et al. (2019):
DEFAULT_MAP = np.array(
            [[0,    0,    0,   0,   0,  0,   0,   0,   0,   0,   0],
             [0.7,  0,    0,   0,   0,  0,   0,   0,   0,   0,   0],
             [-10,  8.2,  0,   0,   0,  0,   0,   0,   0,   0,   0],
             [-10, -10, 11.5,  0,   0,  0,   0,   0,   0,   0,   0],
             [-10, -10, -10, 14.0, 15.1,16.1,0,   0,   0,   0,   0],
             [-10, -10, -10, -10, -10, -10,  0,   0,   0,   0,   0],
             [-10, -10, -10, -10, -10, -10,  0,   0,   0,   0,   0],
             [-10, -10, -10, -10, -10, -10, 19.6, 20.3,0,   0,   0],
             [-10, -10, -10, -10, -10, -10, -10, -10,  0,   0,   0],
             [-10, -10, -10, -10, -10, -10, -10, -10, 22.4, 0,   0],
             [-10, -10, -10, -10, -10, -10, -10, -10, -10, 23.7, 0]]
        )

# As in Vamplew et al. (2018):
CONCAVE_MAP = np.array(
            [[0,    0,    0,   0,   0,  0,   0,   0,   0,   0,   0],
             [1.0,  0,    0,   0,   0,  0,   0,   0,   0,   0,   0],
             [-10,  2.0,  0,   0,   0,  0,   0,   0,   0,   0,   0],
             [-10, -10,  3.0,  0,   0,  0,   0,   0,   0,   0,   0],
             [-10, -10, -10, 5.0,  8.0,16.0, 0 ,  0,   0,   0,   0],
             [-10, -10, -10, -10, -10, -10,  0,   0,   0,   0,   0],
             [-10, -10, -10, -10, -10, -10,  0,   0,   0,   0,   0],
             [-10, -10, -10, -10, -10, -10, 24.0, 50.0,0,   0,   0],
             [-10, -10, -10, -10, -10, -10, -10, -10,  0,   0,   0],
             [-10, -10, -10, -10, -10, -10, -10, -10, 74.0, 0,   0],
             [-10, -10, -10, -10, -10, -10, -10, -10, -10, 124.0,0]]
        )

class DeepSeaTreasure(gym.Env):
    """Deep Sea Treasure environment

    Adapted from: https://github.com/RunzheYang/MORL

    CCS weights: [1,0], [0.7,0.3], [0.67,0.33], [0.6,0.4], [0.56,0.44], [0.52,0.48], [0.5,0.5], [0.4,0.6], [0.3,0.7], [0, 1]
    """

    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 4}

    def __init__(self, dst_map=DEFAULT_MAP, float_state=False):
        self.size = 11
        self.window_size = 512
        self.window = None
        self.clock = None
        self.epsilon = 0.99
        self.epsilonDecrease = 0.99

        self.float_state = float_state

        # The map of the deep sea treasure (convex version)
        self.sea_map = dst_map
        assert self.sea_map.shape == DEFAULT_MAP.shape, "The map shape must be 11x11"
        
        self.dir = {
            0: np.array([-1, 0], dtype=np.int32),  # up
            1: np.array([1, 0], dtype=np.int32),  # down
            2: np.array([0, -1], dtype=np.int32),  # left
            3: np.array([0, 1], dtype=np.int32)  # right
        }

        # state space specification: 2-dimensional discrete box
        obs_type = np.float32 if self.float_state else np.int32
        self.observation_space = Box(low=0.0, high=1.0, shape=(2,), dtype=obs_type)

        # action space specification: 1 dimension, 0 up, 1 down, 2 left, 3 right
        self.action_space = Discrete(4)
        self.reward_space = Box(low=np.array([0, -1]), high=np.array([23.7, -1]), dtype=np.float32)

        self.current_state = np.array([0, 0], dtype=np.int32)

    def get_map_value(self, pos):
        return self.sea_map[pos[0]][pos[1]]

    def is_valid_state(self, state):
        if state[0] >= 0 and state[0] <= 10 and state[1] >= 0 and state[1] <= 10:
            if self.get_map_value(state) != -10:
                return True
        return False
    
    def render(self, mode='human'):
        # The size of a single grid square in pixels
        pix_square_size = self.window_size / self.size
        if self.window is None:
            self.submarine_img = pygame.image.load(str(Path(__file__).parent.absolute()) + '/assets/submarine.png')
            self.submarine_img = pygame.transform.scale(self.submarine_img, (pix_square_size, pix_square_size))
            self.submarine_img = pygame.transform.flip(self.submarine_img, flip_x=True, flip_y=False)
            self.treasure_img = pygame.image.load(str(Path(__file__).parent.absolute()) + '/assets/treasure.png')
            self.treasure_img = pygame.transform.scale(self.treasure_img, (pix_square_size, pix_square_size))

        if self.window is None and mode == "human":
            pygame.init()
            pygame.display.init()
            self.window = pygame.display.set_mode((self.window_size, self.window_size))
        if self.clock is None and mode == "human":
            self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont(None, 30)
        canvas = pygame.Surface((self.window_size, self.window_size))
        canvas.fill((0, 105, 148))

        for i in range(self.sea_map.shape[0]):
            for j in range(self.sea_map.shape[1]):
                if self.sea_map[i,j] == -10:
                    pygame.draw.rect(
                        canvas,
                        (0, 0, 0),
                        pygame.Rect(
                            pix_square_size * np.array([j,i]) + 0.6,
                            (pix_square_size, pix_square_size),
                        ),
                    )
                elif self.sea_map[i,j] != 0:
                   canvas.blit(self.treasure_img, np.array([j,i]) * pix_square_size)
                   img = self.font.render(str(self.sea_map[i,j]), True, (255, 255, 255))
                   canvas.blit(img, np.array([j,i]) * pix_square_size + np.array([5, 20]))
 
        canvas.blit(self.submarine_img, self.current_state[::-1] * pix_square_size)

        for x in range(self.size + 1):
            pygame.draw.line(
                canvas,
                0,
                (0, pix_square_size * x),
                (self.window_size, pix_square_size * x),
                width=1,
            )
            pygame.draw.line(
                canvas,
                0,
                (pix_square_size * x, 0),
                (pix_square_size * x, self.window_size),
                width=1,
            )

        if mode == "human":
            # The following line copies our drawings from `canvas` to the visible window
            self.window.blit(canvas, canvas.get_rect())
            pygame.event.pump()
            pygame.display.update()

            # We need to ensure that human-rendering occurs at the predefined framerate.
            # The following line will automatically add a delay to keep the framerate stable.
            self.clock.tick(self.metadata["render_fps"])
        else:  # rgb_array
            return np.transpose(
                np.array(pygame.surfarray.pixels3d(canvas)), axes=(1, 0, 2)
            )

    def get_state(self):
        if self.float_state:
            state = self.current_state.astype(np.float32) * 0.1
        else:
            state = self.current_state.copy()
        return state

    def reset(self, seed=None, return_info=False, **kwargs):
        super().reset(seed=seed)
        self.np_random.seed(seed)

        self.current_state = np.array([0, 0], dtype=np.int32)
        self.step_count = 0.0
        state = self.get_state()
        return (state, {}) if return_info else state

    def step(self, action):
        next_state = self.current_state + self.dir[action]

        if self.is_valid_state(next_state):
            self.current_state = next_state

        treasure_value = self.get_map_value(self.current_state)
        if treasure_value == 0 or treasure_value == -10:
            treasure_value = 0.0
            terminal = False
        else:
            terminal = True
        time_penalty = -1.0
        vec_reward = np.array([treasure_value, time_penalty], dtype=np.float32)

        state = self.get_state()

        return state, vec_reward, terminal, {}

    def close(self):
        if self.window is not None:
            pygame.display.quit()
            pygame.quit()

    #getNonDominated: Return set of non dominated q-values(s,a)
    def get_NonDominated(self):
        pass

    def get_QValues(self):
        
        reward1 = 0
        reward2 = 0
        
        Q1 = np.zeros([72,4])
        Q2 = np.zeros([72,4])
        Q = np.zeros([72,4])
    # Set learning parameters
        lr = 0.9
        y = 0.95
        num_episodes = 15000
        paretoList=[]
        
        for i in range(num_episodes):
            
            env.reset()
            s=0
            totalTime=0
            
            #Qlearning
            while totalTime<500:
                #tem que ver como pega o estado s
                env.render()
                a = env.get_Action(s)

                s1, vec_reward, terminal, info = env.step(a)
                reward1 = vec_reward[0]
                reward2 = vec_reward[1]
                
                Q1[s,a] = Q1[s,a] + lr*(reward1 + y*np.max(Q1[s1,:]) - Q1[s,a])
                Q2[s,a] = Q2[s,a] + lr*(reward2 + y*np.max(Q2[s1,:]) - Q2[s,a])
                Q[s,a]= reward1*Q1[s,a] + reward2*Q2[s,a]
                s = s1
                #cada linha é um estado e cada coluna é uma ação
                print("\nQ TABLE = ")
                print(Q)
                print("\n\n\n")
                if terminal:
                    env.reset()
                    break

    #TODO (falta adaptar para nossa tabela de q values)
    def get_Action(self,s):
        if np.random.rand() < self.epsilon:
            return env.action_space.sample()
        return np.argmax(s)



if __name__ == '__main__':

    env = DeepSeaTreasure()
    done = False
    env.reset()
    """while True:
        env.render()
        obs, r, done, info = env.step(env.action_space.sample())
        print(r, "REVARDS")
        if done:
            env.reset()
    """
    
    env.get_QValues()