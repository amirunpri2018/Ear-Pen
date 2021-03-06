from imgaug import augmenters as iaa
from imgaug import parameters as iap
from build import nms
import numpy as np
import imgaug
import h5py
import os

temp_file_name1 = 'tmp1.h5'
temp_file_name2 = 'tmp2.h5'

def __load_data(path='./ear_pen.h5'):
    """
        Load the essential training data.
        You shouldn't use this function directly.
        This function is copied from ../load/
    """
    if not os.path.exists(path):
        print('You should generate the ear_pen hdf5 file first...')
        exit()
    with h5py.File(path, 'r') as f:
        return (np.asarray(f['train_x']), np.asarray(f['train_y'])), (np.asarray(f['test_x']), np.asarray(f['test_y']))

def nms_tensor(tensor):
    res = []
    for ann in tensor:
        res.append(nms(ann))
    return np.asarray(res, dtype=np.uint8)

def process1(imgs, anns):
    """
        Generate the training data whose annotations aren't change
        
        Arg:    imgs    - The array of original training images
                anns    - The array of original training annotations
        Ret:    The lists of images and annotations with generated data
    """
    seq_list = [
        iaa.Sometimes(1.0, iaa.Multiply((0.5, 1.5)), name='random multiply'),
        iaa.Sometimes(1.0, iaa.Add(20), name='add 20'),
        iaa.Sometimes(1.0, iaa.GaussianBlur(sigma=(0.5, 1.0), name='random gaussian blur')),
    ]
    origin_imgs = np.copy(imgs)
    origin_anns = np.copy(anns)
    for seq in seq_list:
        seq = seq.to_deterministic()    
        aug_imgs = seq.augment_images(origin_imgs)
        aug_anns = origin_anns
        imgs = np.concatenate((imgs, aug_imgs))
        anns = np.concatenate((anns, aug_anns))
        print('op name: ', seq.name, 'size: ', np.shape(aug_imgs))
    return imgs, anns

def process2(imgs, anns):
    """
        Generate the training data whose annotations would be changed
        
        Arg:    imgs    - The array of original training images
                anns    - The array of original training annotations
        Ret:    The lists of images and annotations with generated data
    """
    origin_batch_num = np.shape(imgs)[0]
    seq_list = [
        iaa.Sequential([iaa.Fliplr(1.0, name='horizontial flip')]),
        iaa.Sequential([iaa.Flipud(1.0, name='vertical flip')]),
        iaa.Sometimes(1.0, iaa.Affine(scale=(0.75, 1.75), name='random affine scale')),
        iaa.Sometimes(1.0, iaa.Affine(translate_percent=(-0.5, 0.5), name='affine translate')),
        iaa.Sometimes(1.0, iaa.Affine(shear=(-45, 45), name='random shear')),
        iaa.Sometimes(1.0, iaa.Affine(order=imgaug.ALL, name='all'))
    ]
    origin_imgs = np.copy(imgs)
    origin_anns = np.copy(anns)
    for seq in seq_list:
        seq = seq.to_deterministic()    
        aug_imgs = seq.augment_images(origin_imgs)
        aug_anns = seq.augment_images(origin_anns)
        aug_anns = nms_tensor(aug_anns)
        imgs = np.concatenate((imgs, aug_imgs))
        anns = np.concatenate((anns, aug_anns))
        print('op name: ', seq.name, 'size: ', np.shape(aug_imgs))
    return imgs[origin_batch_num:, :, :, :], anns[origin_batch_num:, :, :, :]


if __name__ == '__main__':
    # Load data and normalize
    (train_x, train_y), (test_x, test_y) = __load_data()

    # Deal with first part
    print('<< Generate >>')
    aug_imgs, aug_anns = process1(np.copy(train_x), np.copy(train_y))
    with h5py.File(temp_file_name1, 'w') as f:
        f.create_dataset('x', data=aug_imgs)
        f.create_dataset('y', data=aug_anns)
    del aug_imgs
    del aug_anns

    # Deal with second part
    aug_imgs, aug_anns = process2(np.copy(train_x), np.copy(train_y))
    with h5py.File(temp_file_name2, 'w') as f:
        f.create_dataset('x', data=aug_imgs)
        f.create_dataset('y', data=aug_anns)
    del aug_imgs
    del aug_anns
    del train_x
    del train_y
    
    # Merge and store result
    print('<< Merge >>')
    f1 = h5py.File('tmp1.h5')
    f2 = h5py.File('tmp2.h5')    
    train_x = np.concatenate((f1['x'], f2['x']), axis=0)
    train_y = np.concatenate((f1['y'], f2['y']), axis=0)
    with h5py.File('ear_pen.h5', 'w') as f:
        f.create_dataset('train_x', data=train_x)
        f.create_dataset('train_y', data=train_y)
        f.create_dataset('test_x', data=test_x)
        f.create_dataset('test_y', data=test_y)
    print('the shape of the result: ', np.shape(train_x))

    # Delete temp file
    print('<< Remove temp file >>')
    os.remove(temp_file_name1)
    os.remove(temp_file_name2)