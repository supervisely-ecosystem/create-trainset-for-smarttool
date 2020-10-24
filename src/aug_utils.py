import supervisely_lib as sly

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


def aug_project_meta(meta: sly.ProjectMeta, class_name, pos_name, neg_name) -> sly.ProjectMeta:
    obj_class = sly.ObjClass(class_name, sly.Bitmap, color=[0, 0, 255])
    pos = sly.ObjClass(pos_name, sly.Point, color=[0, 255, 0])
    neg = sly.ObjClass(neg_name, sly.Point, color=[255, 0, 0])

    new_meta = sly.ProjectMeta()
    new_meta = new_meta.add_obj_classes([obj_class, neg, pos])

    train_tag = sly.TagMeta('train', sly.TagValueType.NONE)
    val_tag = sly.TagMeta('val', sly.TagValueType.NONE)
    new_meta = new_meta.add_tag_metas([train_tag, val_tag])
    return new_meta, obj_class, pos, neg, train_tag, val_tag


def aug(image, ann: sly.Annotation, obj_class, pos_class, neg_class):
    if len(ann.labels) == 0:
        return []

    # rename to single class
    new_labels = []
    for label in ann.labels:
        new_labels.append(label.clone(obj_class=obj_class))
    res_ann = ann.clone(labels=new_labels)

    