import gymnasium as gym

env = gym.make("HalfCheetah-v5", render_mode="human")

obs, _ = env.reset()

for _ in range(1000):
    action = env.action_space.sample()
    obs, reward, done, truncated, info = env.step(action)
    
    if done or truncated:
        obs, _ = env.reset()

env.close()