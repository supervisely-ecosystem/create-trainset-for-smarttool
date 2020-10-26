import supervisely_lib as sly
import random


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

    def _rand_padding():
        return random.randint(app_state["paddingRange"][0], app_state["paddingRange"][1])

    crop_padding = {
        "top": "{}%".format(_rand_padding()),
        "left": "{}%".format(_rand_padding()),
        "right": "{}%".format(_rand_padding()),
        "bottom": "{}%".format(_rand_padding())
    }
    imgs_anns = sly.aug.instance_crop(img, res_ann, obj_class.name, save_other_classes_in_crop=False, padding_config=crop_padding)
    return imgs_anns