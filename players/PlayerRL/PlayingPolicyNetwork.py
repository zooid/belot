import tensorflow as tf
import numpy as np
from belot import cards

class PlayingPolicyNetwork:

    def __init__(self, name):

        self.inputSize = 360 # veličina stanja
        self.numHiddenNeurons = 32
        self.numOutputNeurons = 32 # broj karata
        self.regLambda = 0.1

        def leaky_relu(x, alpha=0.1):
            return tf.maximum(alpha*x, x)

        with tf.variable_scope("PlayingPolicyNetwork_{}".format(name)):
            self.session=tf.Session()

            self.statePlaceholder = tf.placeholder(dtype=tf.float32, shape=(None, self.inputSize), name="statePlaceholder")
            self.legalMaskPlaceholder = tf.placeholder(dtype=tf.bool, shape=(None, self.numOutputNeurons), name="legalMaskPlaceholder")
            self.rewardPlaceholder = tf.placeholder(dtype=tf.float32, shape=(None,), name="rewardPlaceholder")
            self.actionPlaceholder = tf.placeholder(dtype=tf.int32, shape=(None,), name="actionPlaceholder")

            self.W1 = tf.get_variable(name="W1", shape=(self.inputSize,self.numHiddenNeurons), initializer=tf.contrib.layers.xavier_initializer())
            self.b1 = tf.Variable(initial_value=tf.constant(0.0, shape=(self.numHiddenNeurons,), dtype=tf.float32), name="b1")
            z1 = tf.nn.xw_plus_b(self.statePlaceholder, self.W1, self.b1, name="z1")
            h1 = leaky_relu(z1)

            self.W2 = tf.get_variable(name="W2", shape=(self.numHiddenNeurons, self.numHiddenNeurons), initializer=tf.contrib.layers.xavier_initializer())
            self.b2 = tf.Variable(initial_value=tf.constant(0.0, shape=(self.numHiddenNeurons,), dtype=tf.float32), name="b2")
            z2 = tf.nn.xw_plus_b(h1, self.W2, self.b2, name="z2")
            h2 = leaky_relu(z2)

            self.W3 = tf.get_variable(name="W3", shape=(self.numHiddenNeurons, self.numOutputNeurons), initializer=tf.contrib.layers.xavier_initializer())
            self.b3 = tf.Variable(initial_value=tf.constant(0.0, shape=(self.numOutputNeurons,), dtype=tf.float32), name="b3")
            z3 = tf.nn.xw_plus_b(h2, self.W3, self.b3, name="z3")

            zeros = tf.zeros_like(self.legalMaskPlaceholder, dtype=tf.float32)

            maskedOutput = tf.where(condition = self.legalMaskPlaceholder, x = tf.nn.softmax(z3), y = zeros)
            self.output = maskedOutput / tf.reduce_sum(maskedOutput)
            reshapedOutput = tf.reshape(self.output, shape=(-1,))

            outputShape = tf.shape(self.output)
            batchSize = outputShape[0]

            self.responsibleIndices = tf.range(0, batchSize)*self.numOutputNeurons + self.actionPlaceholder
            self.responsibleNeurons = tf.gather(reshapedOutput, indices=self.responsibleIndices)

            lossL2 = tf.nn.l2_loss(self.W1) + tf.nn.l2_loss(self.W2) + tf.nn.l2_loss(self.W3)

            self.loss = -tf.reduce_mean(tf.log(self.responsibleNeurons + 1e-9) * self.rewardPlaceholder) + self.regLambda * lossL2

            optimizer = tf.train.AdamOptimizer(learning_rate=1e-5)
            self.trainOp = optimizer.minimize(self.loss)

            self.index = tf.argmax(self.output, axis=1)

            self.session.run(tf.global_variables_initializer())

    def train(self, action, state, reward):
        legalMask = np.array([[True for _ in cards]]*len(state))

        loss, _ = self.session.run(
            [self.loss, self.trainOp],
            feed_dict={
                self.actionPlaceholder: action,
                self.statePlaceholder: state,
                self.legalMaskPlaceholder: legalMask,
                self.rewardPlaceholder: reward
            }
        )
        return loss

    def feed(self, state, legalCards):
        legalMask = np.array([[True if card in legalCards else False for card in cards]]*len(state))

        output, index = self.session.run([self.output, self.index], feed_dict={self.statePlaceholder: state, self.legalMaskPlaceholder: legalMask})
        return output[0], index[0]
