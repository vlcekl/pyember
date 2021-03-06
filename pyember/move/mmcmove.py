import numpy as np

class MMCMove:
    """Class managing mmc moves"""


    def __init__(self, moves, config):

        self.moves = []
        self.accepts = []
        self.probs = []

        supported_moves = set([
                'spin_flip_3d'
            ])

        prob_sum = 0.0
        for move_type, prob in moves.items():

            if move_type not in supported_moves:
                raise ValueError(f'Move type {move_type} not supported')

            if move_type == 'spin_flip_3d':
                self.latt_type = 'SC_n3'
                assert config['latt_type'] == self.latt_type, "Move does not match the lattice"
                self.moves.append(self.spin_flip_3d_propose)
                self.accepts.append(self.spin_flip_3d_accept)
            else:
                pass

            self.probs.append(prob)
            prob_sum += prob

        self.probs = np.array(self.probs).astype(np.float64)
        self.probs /= np.sum(self.probs)    # normalize to sum = 1
        self.probs = np.cumsum(self.probs)  # cummulative sum for easy selection

        self.boxvec = np.diag(config['box'])


    def move(self, config):

        # choose move
        self.try_move = np.searchsorted(self.probs, np.random.random())

        # perform move
        event = self.moves[self.try_move](config)

        return event


    def accept(self, config, event, hamilton):
        self.accepts[self.try_move](config, event, hamilton)


    def spin_flip_3d_propose(self, config):
        """Select a random spin from a given configuration and generate its random orientation"""

        ix = np.random.randint(self.boxvec[0])
        iy = np.random.randint(self.boxvec[1])
        iz = np.random.randint(self.boxvec[2])

        # original spin orientation
        so = config['latt_intra'][ix, iy, iz]

        # new spin orientation
        sz = 2*np.random.random() - 1
        st = np.sqrt(1 - sz*sz)
        phi = 2*np.pi*np.random.random()
        sx = st*np.sin(phi)
        sy = st*np.cos(phi)

        # create an event tuple
        event = (
                    ((ix, iy, iz), tuple(so)),      # initial state
                    ((ix, iy, iz), (sx, sy, sz))    # final state
                )

        return event


    def spin_flip_3d_accept(self, config, event, hamilton):

        ri = event[1][0]  # final position
        ix, iy, iz = ri  # final position
        config['latt_intra'][ix, iy, iz,:] = event[1][1]  # assign final spin

        i = config['latt_i'][ix, iy, iz]
        hamilton.energy_i[i] += hamilton.dui[0] + 0.5*np.sum(hamilton.dui[1:])

        for nbr, du in zip(hamilton.nbrlist, hamilton.dui[1:]):
            jx, jy, jz = (np.array(ri) + nbr) % self.boxvec
            j = config['latt_i'][jx, jy, jz]
            hamilton.energy_i[j] += 0.5*du

        hamilton.energy_total += np.sum(hamilton.dui)

