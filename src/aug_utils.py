import supervisely_lib as sly
import random
import numpy as np


def validate_input_meta(meta: sly.ProjectMeta):
    classes_with_unsupported_shape = []

    if len(meta.obj_classes) == 0:
        raise ValueError("There are no classes in project")

    for obj_class in meta.obj_classes:
        if obj_class.geometry_type != sly.Bitmap:
            classes_with_unsupported_shape.append((obj_class.name, obj_class.geometry_type.geometry_name()))

    if len(classes_with_unsupported_shape) > 0:
        raise TypeError('Unsupported shapes: {}. App supports only {}. '
                        'Use another apps to transform class shapes or rasterize objects. Learn more in app readme.'
                        .format(classes_with_unsupported_shape, sly.Bitmap.geometry_name()))


def aug_project_meta(meta: sly.ProjectMeta, app_state):
    obj_class_name = app_state["className"]
    pos_class_name = app_state["posClassName"]
    neg_class_name = app_state["negClassName"]

    obj_class = sly.ObjClass(obj_class_name, sly.Bitmap, color=[0, 0, 255])
    pos = sly.ObjClass(pos_class_name, sly.Point, color=[0, 255, 0])
    neg = sly.ObjClass(neg_class_name, sly.Point, color=[255, 0, 0])

    new_meta = sly.ProjectMeta()
    new_meta = new_meta.add_obj_classes([obj_class, neg, pos])

    train_tag = sly.TagMeta('train', sly.TagValueType.NONE)
    val_tag = sly.TagMeta('val', sly.TagValueType.NONE)
    new_meta = new_meta.add_tag_metas([train_tag, val_tag])
    return new_meta


def ins_crop_and_resize(img, ann, cls_names, crop_conf, resize_conf):
    res_imgs = []
    res_anns = []
    crop_imgs_anns = sly.aug.instance_crop(img, ann, cls_names, padding_config=crop_conf)
    for im_to_resize, ann_to_resize in crop_imgs_anns:
        resize_img, resize_ann = sly.aug.resize(im_to_resize, ann_to_resize, resize_conf)
        res_imgs.append(resize_img)
        res_anns.append(resize_ann)
    return res_imgs, res_anns

def generate_hints(ann, class_to_gen_hints, positive_class, negative_class, min_points_number):
    def generate_points(mask, color=1):
        h, w = mask.shape[:2]
        pos_area = mask.sum()

        def pt_num(cnt=2):
            cs = [int(np.random.exponential(2)) + min_points_number for _ in range(cnt)]
            return cs

        n_pos, n_neg = pt_num()
        n_pos = min(n_pos, pos_area)
        n_neg = min(n_neg, h * w - pos_area)
        positive_points, negative_points = [], []
        if n_pos > 0:
            # @TODO: speed up (np.argwhere, mm); what if pos or neg is missing?
            points = np.argwhere(mask == color)[:, [1, 0]]  # to xy
            positive_points = points[np.random.choice(points.shape[0], n_pos, replace=False), :]
        if n_neg > 0:
            points = np.argwhere(mask != color)[:, [1, 0]]  # to xy
            negative_points = points[np.random.choice(points.shape[0], n_neg, replace=False), :]
        return positive_points, negative_points

    shape_hw = ann.img_size
    new_labels = []
    mask = np.zeros(shape_hw, dtype=np.uint8)

    for fig in ann.labels:
        new_labels.append(fig)
        if fig.obj_class.name == class_to_gen_hints:
            fig.draw(mask, 1)

    def add_pt_figures(pts, obj_class):
        for point in pts:
            new_fig = sly.Point(*point[::-1])
            new_label = sly.Label(new_fig, obj_class)
            new_labels.append(new_label)

    positive_points, negative_points = generate_points(mask)
    add_pt_figures(positive_points, positive_class)
    add_pt_figures(negative_points, negative_class)

    return ann.clone(labels=new_labels)

def aug_img_ann(img, ann: sly.Annotation, new_meta: sly.ProjectMeta, app_state):
    results = []
    if len(ann.labels) == 0:
        return results

    obj_class = new_meta.get_obj_class(app_state["className"])
    pos_class = new_meta.get_obj_class(app_state["posClassName"])
    neg_class = new_meta.get_obj_class(app_state["negClassName"])

    # rename to single class
    new_labels = []
    for label in ann.labels:
        new_labels.append(label.clone(obj_class=obj_class))
    res_ann = ann.clone(labels=new_labels)

    # filter objects by min side
    res_ann = res_ann.filter_labels_by_min_side(app_state["filterThresh"])
    if len(ann.labels) == 0:
       return results

    inputs = []
    for i in range(app_state["imageDuplicate"]):
        inputs.append((img, res_ann))

    # flip
    if app_state["flipHorizontal"] is True:
        img_lr, ann_lr = sly.aug.fliplr(img, res_ann)
        inputs.append((img_lr, ann_lr))

    if app_state["flipVertical"] is True:
        img_ud, ann_ud = sly.aug.flipud(img, res_ann)
        inputs.append((img_ud, ann_ud))

    def _rand_padding():
        return random.randint(app_state["paddingRange"][0], app_state["paddingRange"][1])

    results_imgs_anns = []
    for (input_img, input_ann) in inputs:
        crop_padding = {
            "top": "{}%".format(_rand_padding()),
            "left": "{}%".format(_rand_padding()),
            "right": "{}%".format(_rand_padding()),
            "bottom": "{}%".format(_rand_padding())
        }
        imgs_anns = sly.aug.instance_crop(input_img, input_ann, obj_class.name,
                                          save_other_classes_in_crop=False, padding_config=crop_padding)
        results_imgs_anns.extend(imgs_anns)

    resized_results = []
    resize_config = (app_state["inputHeight"], app_state["inputWidth"])
    for (input_img, input_ann) in results_imgs_anns:
        resize_img, resize_ann = sly.aug.resize(input_img, input_ann, resize_config)
        resized_results.append((resize_img, resize_ann))

    hits_results = []
    for (input_img, input_ann) in resized_results:
        ann_hint = generate_hints(input_ann, obj_class.name, pos_class, neg_class, app_state["minPointsCount"])
        hits_results.append((input_img, ann_hint))

    return hits_results