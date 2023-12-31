import os
import numpy as np
import json
import cv2 as cv2

from config import get_parameters
from utils import visualize_hand_crop, visualize_hand

left_hand = ['left_wrist',
             'left_thumb_1', 'left_thumb_2', 'left_thumb_3', 'left_thumb_4',
             'left_index_1', 'left_index_2', 'left_index_3', 'left_index_4',
             'left_middle_1', 'left_middle_2', 'left_middle_3', 'left_middle_4',
             'left_ring_1', 'left_ring_2', 'left_ring_3', 'left_ring_4',
             'left_pinky_1', 'left_pinky_2', 'left_pinky_3', 'left_pinky_4']
right_hand = ['right_wrist',
             'right_thumb_1', 'right_thumb_2', 'right_thumb_3', 'right_thumb_4',
             'right_index_1', 'right_index_2', 'right_index_3', 'right_index_4',
             'right_middle_1', 'right_middle_2', 'right_middle_3', 'right_middle_4',
             'right_ring_1', 'right_ring_2', 'right_ring_3', 'right_ring_4',
             'right_pinky_1', 'right_pinky_2', 'right_pinky_3', 'right_pinky_4']
both_hand = left_hand + right_hand

hand_link = [[0,1], [1,2], [2,3], [3,4],
             [0,5], [5,6], [6,7], [7,8],
             [0,9], [9,10], [10,11], [11,12],
             [0,13], [13,14], [14,15], [15,16],
             [0,17], [17,18], [18,19], [19,20]]
hand_link_color = [[255,125,0], [255,125,0], [255,125,0], [255,125,0],
                   [255,155,255], [255,155,255], [255,155,255], [255,155,255],
                   [105,175,255], [105,175,255], [105,175,255], [105,175,255],
                   [210,55,60], [210,55,60], [210,55,60], [210,55,60],
                   [0,255,0], [0,255,0], [0,255,0], [0,255,0]]

if __name__ == '__main__':

    args = get_parameters('upenn_0718_Violin_2_5')

    annotation_folder = os.path.join(args.annotation_folder, 'annotation')
    cam_pose_folder = os.path.join(args.annotation_folder, 'camera_pose')
    annotation_image_folder = args.annotation_im_folder

    annotation_files = os.listdir(annotation_folder)

    save_dir = os.path.join(args.video_folder, '../', 'outputs', 'Metashape')
    save_name = 'transformation_MPS_gp_aria.json'
    with open(os.path.join(save_dir, save_name), 'r') as f:
        T_mps_gp_aria = np.array(json.load(f))

    # from metashape calibration
    # TODO: read from file
    K_gp05 = [[879.44310492816487, 0, 1920 / 2 + 6.2943846689491405],
              [0, 879.44310492816487, 1080 / 2 - 1.2995632779780959],
              [0, 0, 1]]
    D_gp05 = [0.088532018586668329, -0.031822959023441059, 0.0054717896597636538, 0]

    # project hand annotation onto aria and dynamic gopro camera
    for file in annotation_files:
        annotation_file = os.path.join(annotation_folder, file)
        with open(annotation_file) as f:
            annot = json.load(f)

        take_uid = annot[list(annot.keys())[0]][0]['metadata']['take_uid']
        take_name = annot[list(annot.keys())[0]][0]['metadata']['take_name']

        if not take_name == 'upenn_0718_Violin_2_5':
            continue

        cam_pose_file = os.path.join(cam_pose_folder, file)
        if not os.path.exists(cam_pose_file):
            print('camera pose not exist for {}, {}'.format(take_uid, take_name))
            continue
        if os.path.exists(cam_pose_file):
            with open(cam_pose_file) as f:
                cam_pose = json.load(f)

        for item in annot.keys():
            hand_3D = np.zeros((42, 5))  # x, y, z, 1, valid
            for idx, joint in enumerate(both_hand):
                if joint in annot[item][0]['annotation3D'].keys():
                    hand_3D[idx, 0] = annot[item][0]['annotation3D'][joint]['x']
                    hand_3D[idx, 1] = annot[item][0]['annotation3D'][joint]['y']
                    hand_3D[idx, 2] = annot[item][0]['annotation3D'][joint]['z']
                    hand_3D[idx, 3] = 1
                    hand_3D[idx, 4] = 1

            K_aria = np.array(cam_pose[item]['aria01']['camera_intrinsics'])
            T_mps_aria_world = np.array(cam_pose[item]['aria01']['camera_extrinsics'])
            hand_3D_repro = K_aria @ T_mps_aria_world @ hand_3D[:, :4].T
            hand_3D_repro = hand_3D_repro[:2, :].T / hand_3D_repro[2:, :].T

            hand_3D_repro = np.concatenate([hand_3D_repro, hand_3D[:, 4:]], axis=-1)
            hand_3D_repro = np.nan_to_num(hand_3D_repro)
            im_name = os.path.join(annotation_image_folder, take_name, '{:06d}.jpg'.format(int(item)))
            im = cv2.imread(im_name)
            im = cv2.rotate(im, cv2.ROTATE_90_COUNTERCLOCKWISE)
            hand_vis = visualize_hand(im, hand_3D_repro[:21, :2])
            hand_vis = visualize_hand(hand_vis, hand_3D_repro[21:, :2])
            hand_vis = cv2.rotate(hand_vis, cv2.ROTATE_90_CLOCKWISE)

            hand_vis_dir = os.path.join(save_dir, '../aria_hand_annot')
            os.makedirs(hand_vis_dir, exist_ok=True)
            cv2.imwrite(os.path.join(hand_vis_dir, '{:06d}.png'.format(int(item))), hand_vis)

            # project to gopro
            T_mps_aria_world = np.concatenate([T_mps_aria_world, np.array([[0, 0, 0, 1]])])
            hand_3D_repro = T_mps_gp_aria[:3, :] @ T_mps_aria_world @ hand_3D[:, :4].T
            hand_3D_repro = hand_3D_repro[:2, :].T / hand_3D_repro[2:, :].T
            hand_3D_repro_distort = cv2.fisheye.distortPoints(np.expand_dims(hand_3D_repro, axis=1), np.array(K_gp05),
                                                              np.array(D_gp05))
            hand_3D_repro_distort = np.nan_to_num(hand_3D_repro_distort)

            im_name = os.path.join(args.video_folder, 'gp05', 'playing_gopro_{:06d}.png'.format(int(item)))
            im = cv2.imread(im_name)
            hand_vis = visualize_hand(im, hand_3D_repro_distort[:21, 0, :2])
            hand_vis = visualize_hand(hand_vis, hand_3D_repro_distort[21:, 0, :2])
            # cv2.imwrite(os.path.join(save_dir, 'gopro_proj.png'), hand_crop)

            hand_vis_dir = os.path.join(save_dir, '../gopro_hand_annot')
            os.makedirs(hand_vis_dir, exist_ok=True)
            cv2.imwrite(os.path.join(hand_vis_dir, '{:06d}.png'.format(int(item))), hand_vis)