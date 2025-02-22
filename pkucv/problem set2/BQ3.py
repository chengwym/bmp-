import cv2
import numpy as np
import multiprocessing as mp
import utils
import constant as const
import stitch
import feature


def panorama360(input_dirname):
    
    pool = mp.Pool(mp.cpu_count())

    img_list, focal_length = utils.parse(input_dirname)

    print('Warp images to cylinder')
    cylinder_img_list = pool.starmap(utils.cylindrical_projection, [(img_list[i], focal_length[i]) for i in range(len(img_list))])
    _, img_width, _ = img_list[0].shape
    stitched_image = cylinder_img_list[0].copy()

    shifts = [[0, 0]]
    cache_feature = [[], []]
    for i in range(1, len(cylinder_img_list)):
        print('Computing .... '+str(i+1)+'/'+str(len(cylinder_img_list)))
        img1 = cylinder_img_list[i-1]
        img2 = cylinder_img_list[i]

        print(' - Find features in previous img .... ', end='', flush=True)
        descriptors1, position1 = cache_feature
        if len(descriptors1) == 0:
            corner_response1 = feature.harris_corner(img1, pool)
            descriptors1, position1 = feature.extract_description(img1, corner_response1, kernel=const.DESCRIPTOR_SIZE, threshold=const.FEATURE_THRESHOLD)
        print(str(len(descriptors1))+' features extracted.')

        print(' - Find features in img_'+str(i+1)+' .... ', end='', flush=True)
        corner_response2 = feature.harris_corner(img2, pool)
        descriptors2, position2 = feature.extract_description(img2, corner_response2, kernel=const.DESCRIPTOR_SIZE, threshold=const.FEATURE_THRESHOLD)
        print(str(len(descriptors2))+' features extracted.')

        cache_feature = [descriptors2, position2]

        if const.DEBUG:
            cv2.imshow('cr1', corner_response1)
            cv2.imshow('cr2', corner_response2)
            cv2.waitKey(0)
        
        print(' - Feature matching .... ', end='', flush=True)
        matched_pairs = feature.matching(descriptors1, descriptors2, position1, position2, pool, y_range=const.MATCHING_Y_RANGE)
        print(str(len(matched_pairs)) +' features matched.')

        if const.DEBUG:
            utils.matched_pairs_plot(img1, img2, matched_pairs)

        print(' - Find best shift using RANSAC .... ', end='', flush=True)
        shift = stitch.RANSAC(matched_pairs, shifts[-1])
        shifts += [shift]
        
        stitched_image = stitch.stitching(stitched_image, img2, shift, pool, blending=True)


    # print('Perform end to end alignment')
    aligned = stitch.end2end_align(stitched_image, shifts)
    # cv2.imwrite('aligned.jpg', aligned)

    print('Cropping image')
    cropped = stitch.crop(aligned)
    cv2.imwrite('panorama_id.png', cropped)

if __name__ == '__main__':
    panorama360('Problem2Images/1')