"""
Copyright 2020 The OneFlow Authors. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import oneflow as flow


def _get_kernel_initializer():
    return flow.variance_scaling_initializer(
        distribution="random_normal", data_format="NCHW"
    )


def _get_regularizer():
    return flow.regularizers.l2(0.00005)


def _get_bias_initializer():
    return flow.zeros_initializer()


def conv2d_layer(
    name,
    input,
    filters,
    kernel_size=3,
    strides=1,
    padding="SAME",
    data_format="NCHW",
    dilation_rate=1,
    activation="Relu",
    use_bias=True,
    weight_initializer=_get_kernel_initializer(),
    bias_initializer=_get_bias_initializer(),
    weight_regularizer=_get_regularizer(),
    bias_regularizer=_get_regularizer(),
):
    if isinstance(kernel_size, int):
        kernel_size_1 = kernel_size
        kernel_size_2 = kernel_size
    if isinstance(kernel_size, list):
        kernel_size_1 = kernel_size[0]
        kernel_size_2 = kernel_size[1]

    weight_shape = (filters, input.shape[1], kernel_size_1, kernel_size_2)
    weight = flow.get_variable(
        name + "-weight",
        shape=weight_shape,
        dtype=input.dtype,
        initializer=weight_initializer,
        regularizer=weight_regularizer,
    )
    output = flow.nn.conv2d(
        input, weight, strides, padding, None, data_format, dilation_rate, name=name
    )
    if use_bias:
        bias = flow.get_variable(
            name + "-bias",
            shape=(filters,),
            dtype=input.dtype,
            initializer=bias_initializer,
            regularizer=bias_regularizer,
        )
        output = flow.nn.bias_add(output, bias, data_format)

    if activation is not None:
        if activation == "Relu":
            output = flow.math.relu(output)
        else:
            raise NotImplementedError

    return output


def conv2d_layer_with_bn(
    name,
    input,
    filters,
    kernel_size=3,
    strides=1,
    padding="SAME",
    data_format="NCHW",
    dilation_rate=1,
    activation="Relu",
    use_bias=True,
    weight_initializer=_get_kernel_initializer(),
    bias_initializer=_get_bias_initializer(),
    weight_regularizer=_get_regularizer(),
    bias_regularizer=_get_regularizer(),
    use_bn=True,
):
    output = conv2d_layer(
        name=name,
        input=input,
        filters=filters,
        kernel_size=kernel_size,
        strides=strides,
        padding=padding,
        data_format=data_format,
        dilation_rate=dilation_rate,
        activation=activation,
        use_bias=use_bias,
        weight_initializer=weight_initializer,
        bias_initializer=bias_initializer,
        weight_regularizer=weight_regularizer,
        bias_regularizer=bias_regularizer,
    )

    if use_bn:
        output = flow.layers.batch_normalization(
            inputs=output,
            axis=1,
            momentum=0.997,
            epsilon=1.001e-5,
            center=True,
            scale=True,
            trainable=True,
            name=name + "_bn",
        )
    return output


def InceptionA(in_blob, index):
    with flow.scope.namespace("mixed_{}".format(index)):
        with flow.scope.namespace("branch1x1"):
            branch1x1 = conv2d_layer(
                "conv0", in_blob, filters=64, kernel_size=1, strides=1, padding="SAME"
            )
        with flow.scope.namespace("branch5x5"):
            branch5x5_1 = conv2d_layer(
                "conv0", in_blob, filters=48, kernel_size=1, strides=1, padding="SAME"
            )
            branch5x5_2 = conv2d_layer(
                "conv1",
                branch5x5_1,
                filters=64,
                kernel_size=5,
                strides=1,
                padding="SAME",
            )
        with flow.scope.namespace("branch3x3dbl"):
            branch3x3dbl_1 = conv2d_layer(
                "conv0", in_blob, filters=64, kernel_size=1, strides=1, padding="SAME"
            )
            branch3x3dbl_2 = conv2d_layer(
                "conv1",
                branch3x3dbl_1,
                filters=96,
                kernel_size=3,
                strides=1,
                padding="SAME",
            )
            branch3x3dbl_3 = conv2d_layer(
                "conv2",
                branch3x3dbl_2,
                filters=96,
                kernel_size=3,
                strides=1,
                padding="SAME",
            )
        with flow.scope.namespace("branch_pool"):
            branch_pool_1 = flow.nn.avg_pool2d(
                in_blob,
                ksize=3,
                strides=1,
                padding="SAME",
                data_format="NCHW",
                name="pool",
            )
            branch_pool_2 = conv2d_layer(
                "conv",
                branch_pool_1,
                filters=32 if index == 0 else 64,
                kernel_size=1,
                strides=1,
                padding="SAME",
            )

        inceptionA_bn = []
        inceptionA_bn.append(branch1x1)
        inceptionA_bn.append(branch5x5_2)
        inceptionA_bn.append(branch3x3dbl_3)
        inceptionA_bn.append(branch_pool_2)

        mixed_concat = flow.concat(values=inceptionA_bn, axis=1, name="concat")

    return mixed_concat


def InceptionB(in_blob, index):
    with flow.scope.namespace("mixed_{}".format(index)):
        with flow.scope.namespace("branch3x3"):
            branch3x3 = conv2d_layer(
                "conv0", in_blob, filters=384, kernel_size=3, strides=2, padding="VALID"
            )
        with flow.scope.namespace("branch3x3dbl"):
            branch3x3dbl_1 = conv2d_layer(
                "conv0", in_blob, filters=64, kernel_size=1, strides=1, padding="SAME"
            )
            branch3x3dbl_2 = conv2d_layer(
                "conv1",
                branch3x3dbl_1,
                filters=96,
                kernel_size=3,
                strides=1,
                padding="SAME",
            )
            branch3x3dbl_3 = conv2d_layer(
                "conv2",
                branch3x3dbl_2,
                filters=96,
                kernel_size=3,
                strides=2,
                padding="VALID",
            )
        with flow.scope.namespace("branch_pool"):
            branch_pool = flow.nn.max_pool2d(
                in_blob,
                ksize=3,
                strides=2,
                padding="VALID",
                data_format="NCHW",
                name="pool0",
            )

        inceptionB_bn = []
        inceptionB_bn.append(branch3x3)
        inceptionB_bn.append(branch3x3dbl_3)
        inceptionB_bn.append(branch_pool)
        mixed_concat = flow.concat(values=inceptionB_bn, axis=1, name="concat")

    return mixed_concat


def InceptionC(in_blob, index, filters):
    with flow.scope.namespace("mixed_{}".format(index)):
        with flow.scope.namespace("branch1x1"):
            branch1x1 = conv2d_layer(
                "conv0", in_blob, filters=192, kernel_size=1, strides=1, padding="SAME"
            )
        with flow.scope.namespace("branch7x7"):
            branch7x7_1 = conv2d_layer(
                "conv0",
                in_blob,
                filters=filters,
                kernel_size=1,
                strides=1,
                padding="SAME",
            )
            branch7x7_2 = conv2d_layer(
                "conv1",
                branch7x7_1,
                filters=filters,
                kernel_size=[1, 7],
                strides=1,
                padding="SAME",
            )
            branch7x7_3 = conv2d_layer(
                "conv2",
                branch7x7_2,
                filters=192,
                kernel_size=[7, 1],
                strides=[1, 1],
                padding="SAME",
            )
        with flow.scope.namespace("branch7x7dbl"):
            branch7x7dbl_1 = conv2d_layer(
                "conv0",
                in_blob,
                filters=filters,
                kernel_size=1,
                strides=1,
                padding="SAME",
            )
            branch7x7dbl_2 = conv2d_layer(
                "conv1",
                branch7x7dbl_1,
                filters=filters,
                kernel_size=[7, 1],
                strides=1,
                padding="SAME",
            )
            branch7x7dbl_3 = conv2d_layer(
                "conv2",
                branch7x7dbl_2,
                filters=filters,
                kernel_size=[1, 7],
                strides=1,
                padding="SAME",
            )
            branch7x7dbl_4 = conv2d_layer(
                "conv3",
                branch7x7dbl_3,
                filters=filters,
                kernel_size=[7, 1],
                strides=1,
                padding="SAME",
            )
            branch7x7dbl_5 = conv2d_layer(
                "conv4",
                branch7x7dbl_4,
                filters=192,
                kernel_size=[1, 7],
                strides=1,
                padding="SAME",
            )
        with flow.scope.namespace("branch_pool"):
            branch_pool_1 = flow.nn.avg_pool2d(
                in_blob,
                ksize=3,
                strides=1,
                padding="SAME",
                data_format="NCHW",
                name="pool",
            )
            branch_pool_2 = conv2d_layer(
                "conv",
                branch_pool_1,
                filters=192,
                kernel_size=[1, 1],
                strides=1,
                padding="SAME",
            )

        inceptionC_bn = []
        inceptionC_bn.append(branch1x1)
        inceptionC_bn.append(branch7x7_3)
        inceptionC_bn.append(branch7x7dbl_5)
        inceptionC_bn.append(branch_pool_2)
        mixed_concat = flow.concat(values=inceptionC_bn, axis=1, name="concat")

    return mixed_concat


def InceptionD(in_blob, index):
    with flow.scope.namespace("mixed_{}".format(index)):
        with flow.scope.namespace("branch3x3"):
            branch3x3_1 = conv2d_layer(
                "conv0", in_blob, filters=192, kernel_size=1, strides=1, padding="SAME"
            )
            branch3x3_2 = conv2d_layer(
                "conv1",
                branch3x3_1,
                filters=320,
                kernel_size=3,
                strides=2,
                padding="VALID",
            )
        with flow.scope.namespace("branch7x7x3"):
            branch7x7x3_1 = conv2d_layer(
                "conv0", in_blob, filters=192, kernel_size=1, strides=1, padding="SAME"
            )
            branch7x7x3_2 = conv2d_layer(
                "conv1",
                branch7x7x3_1,
                filters=192,
                kernel_size=[1, 7],
                strides=1,
                padding="SAME",
            )
            branch7x7x3_3 = conv2d_layer(
                "conv2",
                branch7x7x3_2,
                filters=192,
                kernel_size=[7, 1],
                strides=1,
                padding="SAME",
            )
            branch7x7x3_4 = conv2d_layer(
                "conv3",
                branch7x7x3_3,
                filters=192,
                kernel_size=3,
                strides=2,
                padding="VALID",
            )
        with flow.scope.namespace("branch_pool"):
            branch_pool = flow.nn.max_pool2d(
                in_blob,
                ksize=3,
                strides=2,
                padding="VALID",
                data_format="NCHW",
                name="pool",
            )

        inceptionD_bn = []
        inceptionD_bn.append(branch3x3_2)
        inceptionD_bn.append(branch7x7x3_4)
        inceptionD_bn.append(branch_pool)

        mixed_concat = flow.concat(values=inceptionD_bn, axis=1, name="concat")

    return mixed_concat


def InceptionE(in_blob, index, pooltype):
    with flow.scope.namespace("mixed_{}".format(index)):
        with flow.scope.namespace("branch1x1"):
            branch1x1 = conv2d_layer(
                "conv0", in_blob, filters=320, kernel_size=1, strides=1, padding="SAME"
            )
        with flow.scope.namespace("branch3x3"):
            branch3x3_1 = conv2d_layer(
                "conv0", in_blob, filters=384, kernel_size=1, strides=1, padding="SAME"
            )
            branch3x3_2 = conv2d_layer(
                "conv1",
                branch3x3_1,
                filters=384,
                kernel_size=[1, 3],
                strides=1,
                padding="SAME",
            )
            branch3x3_3 = conv2d_layer(
                "conv2",
                branch3x3_1,
                filters=384,
                kernel_size=[3, 1],
                strides=[1, 1],
                padding="SAME",
            )
            inceptionE_1_bn = []
            inceptionE_1_bn.append(branch3x3_2)
            inceptionE_1_bn.append(branch3x3_3)
            concat_branch3x3 = flow.concat(
                values=inceptionE_1_bn, axis=1, name="concat"
            )
        with flow.scope.namespace("branch3x3dbl"):
            branch3x3dbl_1 = conv2d_layer(
                "conv0", in_blob, filters=448, kernel_size=1, strides=1, padding="SAME"
            )
            branch3x3dbl_2 = conv2d_layer(
                "conv1",
                branch3x3dbl_1,
                filters=384,
                kernel_size=3,
                strides=1,
                padding="SAME",
            )
            branch3x3dbl_3 = conv2d_layer(
                "conv2",
                branch3x3dbl_2,
                filters=384,
                kernel_size=[1, 3],
                strides=1,
                padding="SAME",
            )
            branch3x3dbl_4 = conv2d_layer(
                "conv3",
                branch3x3dbl_2,
                filters=384,
                kernel_size=[3, 1],
                strides=1,
                padding="SAME",
            )
            inceptionE_2_bn = []
            inceptionE_2_bn.append(branch3x3dbl_3)
            inceptionE_2_bn.append(branch3x3dbl_4)
            concat_branch3x3dbl = flow.concat(
                values=inceptionE_2_bn, axis=1, name="concat"
            )
        with flow.scope.namespace("branch_pool"):
            if pooltype == "avg":
                branch_pool_1 = flow.nn.avg_pool2d(
                    in_blob,
                    ksize=3,
                    strides=1,
                    padding="SAME",
                    data_format="NCHW",
                    name="pool",
                )
            elif pooltype == "max":
                branch_pool_1 = flow.nn.max_pool2d(
                    in_blob,
                    ksize=3,
                    strides=1,
                    padding="SAME",
                    data_format="NCHW",
                    name="pool",
                )
            branch_pool_2 = conv2d_layer(
                "conv",
                branch_pool_1,
                filters=192,
                kernel_size=[1, 1],
                strides=1,
                padding="SAME",
            )

        inceptionE_total_bn = []
        inceptionE_total_bn.append(branch1x1)
        inceptionE_total_bn.append(concat_branch3x3)
        inceptionE_total_bn.append(concat_branch3x3dbl)
        inceptionE_total_bn.append(branch_pool_2)

        concat_total = flow.concat(values=inceptionE_total_bn, axis=1, name="concat")

    return concat_total


def inceptionv3(images, trainable=True, channel_last=False):
    if channel_last:
        # if channel_last=True, then change mode from 'nchw' to 'nhwc'
        images = flow.transpose(images, name="transpose", perm=[0, 2, 3, 1])
    with flow.scope.namespace("InceptionV3"):
        # conv0: 299 x 299 x 3
        conv0 = conv2d_layer(
            "conv0", images, filters=32, kernel_size=3, strides=2, padding="VALID"
        )
        conv1 = conv2d_layer(
            "conv1", conv0, filters=32, kernel_size=3, strides=1, padding="VALID"
        )
        conv2 = conv2d_layer(
            "conv2", conv1, filters=64, kernel_size=3, strides=1, padding="SAME"
        )
        pool1 = flow.nn.max_pool2d(
            conv2, ksize=3, strides=2, padding="VALID", data_format="NCHW", name="pool1"
        )
        conv3 = conv2d_layer(
            "conv3", pool1, filters=80, kernel_size=1, strides=1, padding="VALID"
        )
        conv4 = conv2d_layer(
            "conv4", conv3, filters=192, kernel_size=3, strides=1, padding="VALID"
        )
        pool2 = flow.nn.max_pool2d(
            conv4, ksize=3, strides=2, padding="VALID", data_format="NCHW", name="pool2"
        )

        # mixed_0 ~ mixed_2
        mixed_0 = InceptionA(pool2, 0)
        mixed_1 = InceptionA(mixed_0, 1)
        mixed_2 = InceptionA(mixed_1, 2)
        # mixed_3
        mixed_3 = InceptionB(mixed_2, 3)

        # mixed_4 ~ mixed_7
        mixed_4 = InceptionC(mixed_3, 4, 128)
        mixed_5 = InceptionC(mixed_4, 5, 160)
        mixed_6 = InceptionC(mixed_5, 6, 160)
        mixed_7 = InceptionC(mixed_6, 7, 192)

        # mixed_8
        mixed_8 = InceptionD(mixed_7, 8)

        # mixed_9 ~ mixed_10
        mixed_9 = InceptionE(mixed_8, 9, "avg")
        mixed_10 = InceptionE(mixed_9, 10, "max")

        pool3 = flow.nn.avg_pool2d(
            mixed_10,
            ksize=8,
            strides=1,
            padding="VALID",
            data_format="NCHW",
            name="pool3",
        )

        # TODO: Need to transpose weight when converting model from TF to OF if
        # you want to use layers.dense interface.
        fc1 = flow.layers.dense(
            inputs=flow.reshape(pool3, [pool3.shape[0], -1]),
            units=1000,
            activation=None,
            use_bias=True,
            kernel_initializer=flow.truncated_normal(0.816496580927726),
            bias_initializer=flow.constant_initializer(),
            trainable=trainable,
            name="fc1",
        )

    return fc1
