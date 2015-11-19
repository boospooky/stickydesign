from __future__ import division
import os
import pkg_resources
import numpy as np
from .stickydesign import *

nndG37 = np.array([-1.  , -1.44, -1.28, -0.88, -1.45, -1.84, -2.17, -1.28, -1.3 ,
                    -2.24, -1.84, -1.44, -0.58, -1.3 , -1.45, -1.  ])
nndS = np.array([-0.0213, -0.0224, -0.021 , -0.0204, -0.0227, -0.0199, -0.0272,
                    -0.021 , -0.0222, -0.0244, -0.0199, -0.0224, -0.0213, -0.0222,
                    -0.0227, -0.0213])
coaxdG37 = np.array([       -1.04, -2.04, -1.29, -1.27,
                            -0.78, -1.97, -1.44, -1.29,
                            -1.66, -2.70, -1.97, -2.04,
                            -0.12, -1.66, -0.78, -1.04])
coaxdS = 0.0027/0.163 * coaxdG37 # from Zhang, 2009 supp info
coaxddS = coaxdS-nndS
coaxddG37 = coaxdG37-nndG37 # correction term rather than absolute dG

dangle5dG37 = np.array([ -0.51, -0.96, -0.58, -0.5 , 
                            -0.42, -0.52, -0.34, -0.02, 
                            -0.62, -0.72, -0.56,  0.48, 
                            -0.71, -0.58, -0.61, -0.1 ])
dangle5dH = np.array([  0.2, -6.3, -3.7, -2.9,
                             0.6, -4.4, -4. , -4.1, 
                            -1.1, -5.1, -3.9, -4.2, 
                            -6.9, -4. , -4.9, -0.2])
dangle3dG37 = np.array([ -0.12,  0.28, -0.01,  0.13,
                            -0.82, -0.31, -0.01, -0.52,
                            -0.92, -0.23, -0.44, -0.35,
                            -0.48, -0.19, -0.5 , -0.29])
dangle3dH = np.array([ -0.5,  4.7, -4.1, -3.8,
                            -5.9, -2.6, -3.2, -5.2,
                            -2.1, -0.2, -3.9, -4.4,
                            -0.7,  4.4, -1.6,  2.9])
dangle_5end_dS = ( dangle5dH - dangle5dG37 ) / 310.15
dangle_3end_dS = ( dangle3dH - dangle3dG37 ) / 310.15
initdG37 = 1.96
initdS = 0.0057
tailcordG37 = 0.8

class energetics_daoe(object):
    """
Energy functions based on several sources, primarily SantaLucia's 2004 paper,
along with handling of dangles, tails, and nicks specifically for DX tile sticky
ends.
    """
    def __init__(self, temperature=37, mismatchtype='dangle', coaxparams=False):
        if temperature != 37:
            raise NotImplementedError("Temperature adjustment is not yet implemented")
        self.coaxparams = coaxparams

        if mismatchtype == 'max':
            raise NotImplementedError("Max doesn't work yet")
            self.uniform = lambda x,y: np.maximum( self.uniform_loopmismatch(x,y), \
                                                   self.uniform_danglemismatch(x,y) \
                                                 )
        elif mismatchtype == 'loop':
            raise NotImplementedError("Loop doesn't work yet")
            self.uniform = self.uniform_loopmismatch
        elif mismatchtype == 'dangle':
            self.uniform = self.uniform_danglemismatch
        else:
            raise InputError("Mismatchtype {0} is not supported.".format(mismatchtype))

    def matching_uniform(self, seqs):
        ps = pairseqa(seqs)

        # In both cases here, the energy we want is the NN binding energy of each stack,
        if seqs.endtype=='DT':
            dcorr = - dangle3dG37[ps[:,0]] - dangle3dG37[ps.revcomp()[:,0]]
            if self.coaxparams:
                dcorr += coaxddG37[ps[:,0]] + coaxddG37[ps.revcomp()[:,0]]
        elif seqs.endtype=='TD':
            dcorr = - dangle5dG37[ps[:,-1]] - dangle5dG37[ps.revcomp()[:,-1]]
            if self.coaxparams:
                dcorr += coaxddG37[ps[:,-1]] + coaxddG37[ps.revcomp()[:,-1]]
        return -(np.sum(nndG37[ps],axis=1) + initdG37 + dcorr)

    def uniform_loopmismatch(self, seqs1, seqs2):
        if seqs1.shape != seqs2.shape:
            if seqs1.ndim == 1:
                seqs1 = endarray( np.repeat(np.array([seqs1]),seqs2.shape[0],0), seqs1.endtype )
            else:
                raise InputError("Lengths of sequence arrays are not acceptable.")
        assert seqs1.endtype == seqs2.endtype
        endtype = seqs1.endtype

        endlen = seqs1.endlen
        plen = endlen-1

        # TODO: replace this with cleaner code
        if endtype=='DT':
            ps1 = seqs1[:,1:-1]*4+seqs1[:,2:]
            pa1 = seqs1[:,0]*4+seqs1[:,1]
            pac1 = (3-seqs1[:,0])*4+seqs2[:,-1]
            ps2 = seqs2[:,::-1][:,:-2]*4+seqs2[:,::-1][:,1:-1]
            pa2 = seqs2[:,0]*4+seqs2[:,1]
            pac2 = (3-seqs2[:,0])*4+seqs1[:,-1]
        if endtype=='TD':
            ps1 = seqs1[:,:-2]*4+seqs1[:,1:-1]
            pa1 = seqs1[:,-2]*4+seqs1[:,-1]
            pac1 = seqs2[:,0]*4+(3-seqs1[:,-1])
            ps2 = seqs2[:,::-1][:,1:-1]*4+seqs2[:,::-1][:,2:]
            pa2 = seqs2[:,-2]*4+seqs2[:,-1]
            pac2 = (seqs1[:,-1])*4+(3-seqs2[:,-1])

        # Shift here is considering the first strand as fixed, and the second one as
        # shifting.  The shift is the offset of the bottom one in terms of pair
        # sequences (thus +2 and -1 instead of +1 and 0).
        en = np.zeros( (ps1.shape[0], 2*plen) )
        for shift in range(-plen+1,plen):
            en[:,plen+shift-1] = np.sum( \
                    nndG37_full[ ps1[:,max(shift,0):plen+shift], \
                               ps2[:,max(-shift,0):plen-shift] ], \
                               axis=1)
        en[:,plen-1] = en[:,plen-1] + nndG37_full[pa1,pac1] + nndG37_full[pa2,pac2]
        return np.amax(en,1) - self.initdG

    def uniform_danglemismatch(self, seqs1,seqs2,fast=True):
        if seqs1.shape != seqs2.shape:
            if seqs1.ndim == 1:
                seqs1 = endarray( np.repeat(np.array([seqs1]),seqs2.shape[0],0), seqs1.endtype )
            else:
                raise InputError("Lengths of sequence arrays are not acceptable.")
        assert seqs1.endtype == seqs2.endtype
        endtype = seqs1.endtype
        s1 = tops(seqs1)
        s2 = tops(seqs2)
        l = s1.shape[1]
        s2r = np.fliplr(np.invert(s2)%16)
        s2r = s2r//4 + 4*(s2r%4)
        m = np.zeros((s1.shape[0],2*np.sum(np.arange(2,l+1))+l+1))
        r = np.zeros(m.shape[0])
        z = 0;
        if endtype == 'TD':
            s1c = s1[:,0:-1]
            s2rc = s2r[:,1:]
            s1l = np.hstack(( (4*(s2r[:,0]//4) + s1[:,0]//4).reshape(-1,1) , s1 ))
            s2rl = np.hstack(( s2r , (4*(s2r[:,-1]%4) + s1[:,-1]%4).reshape(-1,1) ))
        elif endtype == 'DT':
            s1c = s1[:,1:]
            s2rc = s2r[:,0:-1]
            s2rl = np.hstack(( (4*(s1[:,0]//4) + s2r[:,0]//4).reshape(-1,1) , s2r ))
            s1l = np.hstack(( s1 , (4*(s1[:,-1]%4) + s2r[:,-1]%4).reshape(-1,1) ))
        for o in range(1,l-1):
            zn = l-1-o
            m[:,z:z+zn] = ( s1c[:,:-o]==s2rc[:,o:] ) * -nndG37[s1c[:,:-o]] # - for positive sign
            if endtype == 'DT': # squish offset
                m[:,z] += (m[:,z]!=0) * ( -nndG37[s1[:,0]] - tailcordG37 + dangle3dG37[s1[:,0]] ) # - for positive sign
                m[:,z+zn-1] += (m[:,z+zn-1]!=0) * ( -nndG37[s2[:,0]] - tailcordG37 + dangle3dG37[s2[:,0]] ) # - for positive sign
            if endtype == 'TD': # stretch offset
                m[:,z] += (m[:,z]!=0) * ( -dangle3dG37[s1c[:,-o]] ) # - for positive sign
                m[:,z+zn-1] += (m[:,z+zn-1]!=0) * ( -dangle3dG37[s2[:,-o-1]] ) # - for positive sign
            z = z+zn+2
            m[:,z:z+zn] = ( s2rc[:,:-o]==s1c[:,o:] ) * -nndG37[s2rc[:,:-o]] # - for positive sign
            if endtype == 'DT': # stretch offset
                m[:,z] += (m[:,z]!=0) * ( -dangle5dG37[s1c[:,o-1]] ) # - for positive sign
                m[:,z+zn-1] += (m[:,z+zn-1]!=0) * ( -dangle5dG37[s2[:,o]]) # - for positive sign
            if endtype == 'TD': # squish offset
                m[:,z] += (m[:,z]!=0) * ( -nndG37[s1[:,-1]] - tailcordG37 +dangle5dG37[s1[:,-1]] ) # - for positive sign
                m[:,z+zn-1] += (m[:,z+zn-1]!=0) * ( -nndG37[s2[:,-1]] - tailcordG37 + dangle5dG37[s2[:,-1]]) # - for positive sign
            z = z+zn+2
        # The zero shift case
        m[:,z:z+l+1] = - ( (s1l == s2rl) * nndG37[s1l] )# - for positive sign
        if endtype == 'DT':
            m[:,z] += (m[:,z]!=0)*(+ dangle3dG37[s1[:,0]] - self.coaxparams*coaxddG37[s1[:,0]]) # sign reversed
            m[:,z+l] += (m[:,z+l]!=0)*(+ dangle3dG37[s2[:,0]] - self.coaxparams*coaxddG37[s2[:,0]]) # sign reversed
        if endtype == 'TD':
            m[:,z] += + (m[:,z]!=0)*(dangle5dG37[s1[:,-1]] - self.coaxparams*coaxddG37[s1[:,-1]]) # sign reversed
            m[:,z+l] += + (m[:,z+l]!=0)*(dangle5dG37[s2[:,-1]] - self.coaxparams*coaxddG37[s2[:,-1]]) # sign reversed
        i = 0
        im = len(m)
        from ._stickyext import fastsub
        x = m
        fastsub(x,r)

        return r-initdG37

    def _other_uniform_loopmismatch(self, seqs1, seqs2):
        if seqs1.shape != seqs2.shape:
            if seqs1.ndim == 1:
                seqs1 = endarray( np.repeat(np.array([seqs1]),seqs2.shape[0],0), seqs1.endtype )
            else:
                raise InputError("Lengths of sequence arrays are not acceptable.")
        assert seqs1.endtype == seqs2.endtype
        assert seqs1.endlen == seqs2.endlen
        endtype = seqs1.endtype
        endlen = seqs1.endlen

        ps1 = pairseqa(seqs1); ps2 = pairseqa(seqs2)

        en = np.zeros( (ps1.shape[0], 2*plen) )
        #for shift in range(-plen)

    def _other_uniform_danglemismatch(self, seqs1, seqs2):
        if seqs1.shape != seqs2.shape:
            if seqs1.ndim == 1:
                seqs1 = endarray( np.repeat(np.array([seqs1]),seqs2.shape[0],0), seqs1.endtype )
            else:
                raise InputError("Lengths of sequence arrays are not acceptable.")
        assert seqs1.endtype == seqs2.endtype
        assert seqs1.endlen == seqs2.endlen
        endtype = seqs1.endtype
        endlen = seqs1.endlen

        seqs2rc = (3-seqs2)[::-1] # revcomp of seqs2

        ps1 = pairseqa(seqs1)
        ps2 = pairseqa(seqs2rc)

        if endtype == 'DT':
            # First, we'll start with the non-shift case.
            
            # These are the regions that will match.
            s1 = np.hstack( ( ps1[:,:-1], seqs1[:,-2]*4+seqs2rc[:,-1] ) )
            s2 = np.hstack( ( seqs1[:,0]*4+seqs2rc[:,1], ps2[:,1:] ) )

            # This is our matching area.
            m = (s1 == s2)

            # Any match at 0 or -1 needs to be adjusted by dangle and possibly coax.
            # Otherwise, we just take the dG values
            e = nndG37[m]
            dcorr1 = - dangle3dG37[s1[:,0]]
            dcorr2 = - dangle3dG37[seqs2[:,0]*4+seqs2[:,1]]
            if self.coaxparams:
                dcorr1 += coaxddG37[s1[:,0]]
                dcorr2 += coaxddG37[seqs2[:,0]*4+seqs2[:,1]]
            e[:,0] = m[:,0]*dcorr1
            e[:,-1] += m[:,0]*dcorr2
            
            # Now, whenever we 