import multiprocessing as mp
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import time

def plot_dashboard(data_queue: mp.Queue):
    # Joint names and colors
    joint_names = [
        "left_hip_pitch", "left_hip_yaw", "left_hip_roll", "left_knee_pitch",
        "left_ankle_pitch", "right_hip_pitch", "right_hip_yaw", "right_hip_roll",
        "right_knee_pitch", "right_ankle_pitch"
    ]
    num_joints = len(joint_names)
    joint_colors = plt.cm.get_cmap('tab10', num_joints)

    # Initialize data storage with 1-second window
    max_time_window = 1.0
    time_data = []
    freq_data = []
    position_time = []
    positions = []
    desired_positions = []
    velocity_time = []
    velocities = []

    # Create three separate figures
    fig_freq = plt.figure(figsize=(12, 3))
    fig_pos = plt.figure(figsize=(12, 6))
    fig_vel = plt.figure(figsize=(12, 6))

    # Graph 1: Inference speed
    ax_freq = fig_freq.add_subplot(111)
    ax_freq.set_title('Inference Speed Over Time')
    ax_freq.set_xlabel('Time (s)')
    ax_freq.set_ylabel('Frequency (Hz)')
    ax_freq.axhline(y=50, color='r', linestyle='--', label='50 Hz Reference')
    line_freq, = ax_freq.plot([], [], label='Actual Frequency')
    ax_freq.legend()

    # Graph 2: Joint Positions with dual y-axes
    ax_pos = fig_pos.add_subplot(111)
    ax_pos_deg = ax_pos.twinx()  # Create twin axis for degrees
    ax_pos.set_title('Joint Positions Over Time')
    ax_pos.set_xlabel('Time (s)')
    ax_pos.set_ylabel('Position (rad)')
    ax_pos_deg.set_ylabel('Position (deg)')
    lines_positions = []
    for i in range(num_joints):
        color = joint_colors(i)
        line_pos, = ax_pos.plot([], [], label=f"{joint_names[i]} Actual", color=color)
        line_desired_pos, = ax_pos.plot([], [], linestyle='--', label=f"{joint_names[i]} Desired", color=color)
        lines_positions.append((line_pos, line_desired_pos))
    ax_pos.legend(loc='center left', bbox_to_anchor=(1.02, 0.5))

    # Graph 3: Joint Velocities with dual y-axes
    ax_vel = fig_vel.add_subplot(111)
    ax_vel_deg = ax_vel.twinx()  # Create twin axis for degrees/s
    ax_vel.set_title('Joint Velocities Over Time')
    ax_vel.set_xlabel('Time (s)')
    ax_vel.set_ylabel('Velocity (rad/s)')
    ax_vel_deg.set_ylabel('Velocity (deg/s)')
    lines_velocities = []
    for i in range(num_joints):
        color = joint_colors(i)
        line_vel, = ax_vel.plot([], [], label=f"{joint_names[i]}", color=color)
        lines_velocities.append(line_vel)
    ax_vel.legend(loc='center left', bbox_to_anchor=(1.02, 0.5))

    def rad2deg(rad):
        return rad * 180.0 / np.pi

    def update(frame):
        current_time = time.time()

        # Remove old data outside the time window
        def prune_data(time_array, *data_arrays):
            while time_array and (current_time - time_array[0]) > max_time_window:
                time_array.pop(0)
                for data_array in data_arrays:
                    data_array.pop(0)

        # Prune old data
        prune_data(time_data, freq_data)
        prune_data(position_time, positions, desired_positions)
        prune_data(velocity_time, velocities)

        # Get new data from queue
        while not data_queue.empty():
            try:
                data_type, data = data_queue.get_nowait()
                if data_type == 'frequency':
                    t, freq = data
                    time_data.append(t)
                    freq_data.append(freq)
                elif data_type == 'positions':
                    t, pos, desired_pos = data
                    position_time.append(t)
                    positions.append(pos)
                    desired_positions.append(desired_pos)
                elif data_type == 'velocities':
                    t, vel = data
                    velocity_time.append(t)
                    velocities.append(vel)
            except Exception as e:
                print(f"Error processing queue data: {e}")

        # Update frequency plot
        if time_data and freq_data:
            ax_freq.clear()
            ax_freq.set_title('Inference Speed Over Time')
            ax_freq.set_xlabel('Time (s)')
            ax_freq.set_ylabel('Frequency (Hz)')
            ax_freq.axhline(y=50, color='r', linestyle='--', label='50 Hz Reference')
            ax_freq.plot(time_data, freq_data, label='Actual Frequency')
            ax_freq.legend()
            ax_freq.set_xlim(current_time - max_time_window, current_time)
            ax_freq.set_ylim(0, 60)  # Fixed y-axis limits for frequency

        # Update positions plot
        if position_time and positions and desired_positions:
            ax_pos.clear()
            ax_pos_deg.clear()
            ax_pos.set_title('Joint Positions Over Time')
            ax_pos.set_xlabel('Time (s)')
            ax_pos.set_ylabel('Position (rad)')
            ax_pos_deg.set_ylabel('Position (deg)')
            
            # Store y limits for synchronizing axes
            y_min_rad = float('inf')
            y_max_rad = float('-inf')
            
            for i in range(num_joints):
                color = joint_colors(i)
                joint_actual_positions = [pos[i] for pos in positions]
                joint_desired_positions = [dpos[i] for dpos in desired_positions]
                
                # Update y limits
                y_min_rad = min(y_min_rad, min(joint_actual_positions + joint_desired_positions))
                y_max_rad = max(y_max_rad, max(joint_actual_positions + joint_desired_positions))
                
                ax_pos.plot(position_time, joint_actual_positions, 
                          label=f"{joint_names[i]} Actual", color=color)
                ax_pos.plot(position_time, joint_desired_positions, 
                          linestyle='--', label=f"{joint_names[i]} Desired", color=color)
            
            # Set limits and ticks for both axes
            ax_pos.set_xlim(current_time - max_time_window, current_time)
            ax_pos.set_ylim(y_min_rad, y_max_rad)
            ax_pos_deg.set_ylim(rad2deg(y_min_rad), rad2deg(y_max_rad))
            
            # Add grid
            ax_pos.grid(True, alpha=0.3)
            ax_pos.legend(loc='center left', bbox_to_anchor=(1.02, 0.5))

        # Update velocities plot
        if velocity_time and velocities:
            ax_vel.clear()
            ax_vel_deg.clear()
            ax_vel.set_title('Joint Velocities Over Time')
            ax_vel.set_xlabel('Time (s)')
            ax_vel.set_ylabel('Velocity (rad/s)')
            ax_vel_deg.set_ylabel('Velocity (deg/s)')
            
            # Store y limits for synchronizing axes
            y_min_rad = float('inf')
            y_max_rad = float('-inf')
            
            for i in range(num_joints):
                color = joint_colors(i)
                joint_velocities = [vel[i] for vel in velocities]
                
                # Update y limits
                y_min_rad = min(y_min_rad, min(joint_velocities))
                y_max_rad = max(y_max_rad, max(joint_velocities))
                
                ax_vel.plot(velocity_time, joint_velocities, 
                          label=f"{joint_names[i]}", color=color)
            
            # Set limits and ticks for both axes
            ax_vel.set_xlim(current_time - max_time_window, current_time)
            ax_vel.set_ylim(y_min_rad, y_max_rad)
            ax_vel_deg.set_ylim(rad2deg(y_min_rad), rad2deg(y_max_rad))
            
            # Add grid
            ax_vel.grid(True, alpha=0.3)
            ax_vel.legend(loc='center left', bbox_to_anchor=(1.02, 0.5))

        # Adjust layouts
        fig_freq.tight_layout()
        fig_pos.tight_layout()
        fig_vel.tight_layout()

        # Add padding for legends
        fig_pos.subplots_adjust(right=0.85)
        fig_vel.subplots_adjust(right=0.85)

    # Create animations for each figure
    ani_freq = animation.FuncAnimation(fig_freq, update, interval=100)
    ani_pos = animation.FuncAnimation(fig_pos, update, interval=100)
    ani_vel = animation.FuncAnimation(fig_vel, update, interval=100)

    plt.show()

def run_dashboard():
    data_queue = mp.Queue()
    plot_process = mp.Process(target=plot_dashboard, args=(data_queue,))
    plot_process.start()
    return data_queue

if __name__ == '__main__':
    run_dashboard()
